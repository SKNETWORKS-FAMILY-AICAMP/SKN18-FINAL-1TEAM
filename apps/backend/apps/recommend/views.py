import logging
from typing import Dict, List

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.models import Land
from apps.listings.neo4j_client import Neo4jClient
from apps.listings.serializers import LandSerializer
from apps.users.models import PreferenceSurvey

logger = logging.getLogger(__name__)

RANK_WEIGHT = {
    1: 3,
    2: 2,
    3: 1,
}

LABEL_TO_METRIC = {
    "safty": "Safety",
    "safety": "Safety",
    "치안/안전": "Safety",
    "livingconvenience": "LivingConvenience",
    "convenience": "LivingConvenience",
    "편의시설": "LivingConvenience",
    "pet": "Pet",
    "반려동물": "Pet",
    "traffic": "Traffic",
    "대중교통": "Traffic",
    "culture": "Culture",
    "문화시설": "Culture",
}


def build_weighted_metrics(priorities: Dict[str, int]) -> List[Dict[str, float]]:
    weighted_metrics: Dict[str, float] = {}
    for label, rank in priorities.items():
        if rank is None:
            continue
        metric = LABEL_TO_METRIC.get(str(label).strip().lower())
        if not metric:
            continue
        weight = RANK_WEIGHT.get(int(rank), 0)
        if weight <= 0:
            continue
        weighted_metrics[metric] = max(weighted_metrics.get(metric, 0), weight)
    return [{"name": name, "weight": weight} for name, weight in weighted_metrics.items()]


class RecommendedListingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        address_filter = request.query_params.get("address")
        deal_type = request.query_params.get("deal_type")
        building_type = request.query_params.get("building_type")
        search = request.query_params.get("search")
        latest_survey = (
            PreferenceSurvey.objects.filter(user=request.user)
            .order_by("-created_at")
            .first()
        )
        if not latest_survey or not latest_survey.priorities:
            return Response({"count": 0, "results": []})

        weighted_metrics = build_weighted_metrics(latest_survey.priorities)
        if not weighted_metrics:
            return Response({"count": 0, "results": []})

        lands_queryset = Land.objects.with_images().select_related("landbroker")
        has_filters = bool(address_filter or deal_type or building_type or search)

        if address_filter:
            lands_queryset = lands_queryset.filter(address__icontains=address_filter)

        if deal_type:
            if deal_type == "전월세":
                lands_queryset = lands_queryset.filter(deal_type__icontains="전월세")
            elif deal_type == "미분류":
                lands_queryset = lands_queryset.filter(Q(deal_type__isnull=True) | Q(deal_type=""))
            else:
                lands_queryset = lands_queryset.filter(deal_type=deal_type)

        if building_type:
            lands_queryset = lands_queryset.filter(building_type=building_type)

        if search:
            lands_queryset = lands_queryset.filter(
                Q(address__icontains=search) | Q(land_num__icontains=search)
            )

        land_nums: List[str] = []
        try:
            driver = Neo4jClient.get_driver()
            with driver.session() as session:
                if has_filters:
                    candidate_land_nums = list(
                        lands_queryset.values_list("land_num", flat=True)[:5000]
                    )
                    if not candidate_land_nums:
                        return Response({"count": 0, "results": []})
                    query = """
                    UNWIND $weighted_metrics AS wm
                    MATCH (p:Property)-[r:HAS_TEMPERATURE]->(m:Metric {name: wm.name})
                    WHERE p.id IN $candidate_land_nums
                    WITH p, sum(coalesce(r.temperature, 0) * wm.weight) AS score
                    ORDER BY score DESC
                    LIMIT $limit
                    RETURN p.id AS land_num, score
                    """
                    result = session.run(
                        query,
                        weighted_metrics=weighted_metrics,
                        candidate_land_nums=candidate_land_nums,
                        limit=limit,
                    )
                    land_nums = [record["land_num"] for record in result]
                else:
                    query = """
                    UNWIND $weighted_metrics AS wm
                    MATCH (p:Property)-[r:HAS_TEMPERATURE]->(m:Metric {name: wm.name})
                    WITH p, sum(coalesce(r.temperature, 0) * wm.weight) AS score
                    ORDER BY score DESC
                    LIMIT $limit
                    RETURN p.id AS land_num, score
                    """
                    result = session.run(
                        query,
                        weighted_metrics=weighted_metrics,
                        limit=limit,
                    )
                    land_nums = [record["land_num"] for record in result]
        except Exception as exc:
            logger.error("Failed to fetch recommended listings: %s", exc)
            return Response({"count": 0, "results": []})

        if not land_nums:
            return Response({"count": 0, "results": []})

        lands = lands_queryset.filter(land_num__in=land_nums)
        land_map = {land.land_num: land for land in lands}
        ordered_lands = [land_map[num] for num in land_nums if num in land_map][:limit]

        serializer = LandSerializer(ordered_lands, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})
