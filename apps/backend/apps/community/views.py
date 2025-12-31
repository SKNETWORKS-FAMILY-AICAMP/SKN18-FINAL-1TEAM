from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import F

from .models import CommunityPost, CommunityComment, CommunityPostLike
from .serializers import (
    CommunityPostSerializer,
    CommunityPostListSerializer,
    CommunityCommentSerializer
)


class CommunityPostListCreateView(generics.ListCreateAPIView):
    """
    커뮤니티 게시글 목록 조회 / 생성
    - GET: 삭제되지 않은 게시글 목록
    - POST: 새 게시글 작성 (로그인 필요)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = None
    serializer_class = CommunityPostListSerializer

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommunityPostSerializer
        return CommunityPostListSerializer

    def get_queryset(self):
        """게시판 및 지역 필터에 따른 게시글 반환"""
        queryset = CommunityPost.objects.filter(is_deleted=False).select_related('user').prefetch_related('likes', 'comments')
        board = self.request.query_params.get('board')
        if board in ['free', 'region']:
            queryset = queryset.filter(board_type=board)
        region = self.request.query_params.get('region')
        if region:
            queryset = queryset.filter(region=region)
        dong = self.request.query_params.get('dong')
        if dong:
            queryset = queryset.filter(dong=dong)
        complex_name = self.request.query_params.get('complex_name')
        if complex_name:
            queryset = queryset.filter(complex_name__icontains=complex_name)
        return queryset

    def perform_create(self, serializer):
        """게시글 작성 시 사용자와 게시판 종류 설정"""
        board_type = serializer.validated_data.get('board_type', 'free')
        if board_type != 'region':
            serializer.save(
                user=self.request.user,
                board_type='free',
                region=None,
                dong=None,
                complex_name=None
            )
        else:
            serializer.save(user=self.request.user, board_type='region')


class CommunityPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    커뮤니티 게시글 상세 조회 / 수정 / 삭제
    - GET: 게시글 상세 (조회수 증가)
    - PATCH: 게시글 수정 (작성자만)
    - DELETE: 게시글 삭제 (작성자만, 소프트 삭제)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CommunityPostSerializer

    def get_queryset(self):
        """삭제되지 않은 게시글만 반환"""
        return CommunityPost.objects.filter(is_deleted=False).select_related('user').prefetch_related('likes', 'comments')

    def retrieve(self, request, *args, **kwargs):
        """게시글 조회 시 조회수 증가"""
        instance = self.get_object()
        CommunityPost.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        instance.refresh_from_db(fields=['view_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        """작성자만 수정 가능"""
        if serializer.instance.user != self.request.user:
            raise PermissionDenied("작성자만 수정할 수 있습니다.")
        serializer.save()

    def perform_destroy(self, instance):
        """소프트 삭제 (실제로는 is_deleted=True로 변경)"""
        if instance.user != self.request.user:
            raise PermissionDenied("작성자만 삭제할 수 있습니다.")
        instance.is_deleted = True
        instance.save()


class CommunityCommentView(APIView):
    """
    커뮤니티 댓글 목록 조회 / 생성
    - GET: 특정 게시글의 댓글 목록
    - POST: 새 댓글 작성 (로그인 필요)
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, post_id):
        """게시글의 댓글 목록 조회"""
        post = get_object_or_404(CommunityPost, id=post_id, is_deleted=False)
        comments = post.comments.filter(is_deleted=False)
        serializer = CommunityCommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, post_id):
        """댓글 작성"""
        post = get_object_or_404(CommunityPost, id=post_id, is_deleted=False)
        serializer = CommunityCommentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, post=post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CommunityCommentDetailView(APIView):
    """
    커뮤니티 댓글 수정 / 삭제
    - PATCH: 댓글 수정 (작성자만)
    - DELETE: 댓글 삭제 (작성자만, 소프트 삭제)
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, comment_id):
        """댓글 수정"""
        comment = get_object_or_404(CommunityComment, id=comment_id, is_deleted=False)
        if comment.user != request.user:
            raise PermissionDenied("작성자만 수정할 수 있습니다.")
        
        serializer = CommunityCommentSerializer(comment, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, comment_id):
        """댓글 삭제 (소프트 삭제)"""
        comment = get_object_or_404(CommunityComment, id=comment_id, is_deleted=False)
        if comment.user != request.user:
            raise PermissionDenied("작성자만 삭제할 수 있습니다.")
        
        comment.is_deleted = True
        comment.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommunityPostLikeView(APIView):
    """커뮤니티 게시글 좋아요"""
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        """좋아요 +1"""
        post = get_object_or_404(CommunityPost, id=post_id, is_deleted=False)
        like, created = CommunityPostLike.objects.get_or_create(post=post, user=request.user)
        if created:
            CommunityPost.objects.filter(pk=post.pk).update(like_count=F('like_count') + 1)
            post.refresh_from_db(fields=['like_count'])
        else:
            post.refresh_from_db(fields=['like_count'])
        return Response({'liked': True, 'like_count': post.like_count})

    def delete(self, request, post_id):
        """좋아요 -1 (최소 0 유지)"""
        post = get_object_or_404(CommunityPost, id=post_id, is_deleted=False)
        try:
            like = CommunityPostLike.objects.get(post=post, user=request.user)
        except CommunityPostLike.DoesNotExist:
            post.refresh_from_db(fields=['like_count'])
            return Response({'liked': False, 'like_count': post.like_count})

        like.delete()
        CommunityPost.objects.filter(pk=post.pk, like_count__gt=0).update(like_count=F('like_count') - 1)
        post.refresh_from_db(fields=['like_count'])
        return Response({'liked': False, 'like_count': post.like_count})
