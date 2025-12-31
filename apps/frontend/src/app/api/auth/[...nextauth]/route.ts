import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";
import axios from "axios";

console.log("GOOGLE_CLIENT_ID:", process.env.GOOGLE_CLIENT_ID ? "Loaded" : "Missing");
console.log("GOOGLE_CLIENT_SECRET:", process.env.GOOGLE_CLIENT_SECRET ? "Loaded" : "Missing");

const handler = NextAuth({
    providers: [
        GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID ?? "",
            clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
        }),
        CredentialsProvider({
            name: "Credentials",
            credentials: {
                email: { label: "이메일", type: "email", placeholder: "example@email.com" },
                password: { label: "비밀번호", type: "password" },
            },
            async authorize(credentials) {
                if (!credentials?.email || !credentials.password) {
                    throw new Error("이메일과 비밀번호를 입력해주세요.");
                }

                try {
                    const serverApiUrl = process.env.SERVER_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                    const response = await axios.post(
                        `${serverApiUrl}/api/users/auth/login/`,
                        {
                            email: credentials.email,
                            password: credentials.password,
                        }
                    );

                    const data = response.data;

                    return {
                        id: data.user.id,
                        email: data.user.email,
                        name: data.user.username,
                        image: data.user.profile_image_data || data.user.profile_image,
                        accessToken: data.tokens.access,
                        refreshToken: data.tokens.refresh,
                        isNewUser: data.isNewUser,
                        surveyCompleted: data.surveyCompleted,
                        userId: data.user.id,
                    };
                } catch (error) {
                    console.error("Credential login failed:", error);
                    if (axios.isAxiosError(error)) {
                        throw new Error(error.response?.data?.detail ?? "이메일 또는 비밀번호가 올바르지 않습니다.");
                    }
                    throw new Error("이메일 또는 비밀번호가 올바르지 않습니다.");
                }
            },
        }),
    ],
    callbacks: {
        async signIn({ user, account, profile }) {
            if (account?.provider === "google") {
                try {
                    // 서버 사이드 API 호출: 도커 환경에서는 backend:8000 사용
                    const serverApiUrl = process.env.SERVER_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                    const endpoint = `${serverApiUrl}/api/users/auth/google/`;

                    console.log("=== Google Login Debug ===");
                    console.log("Server API URL:", serverApiUrl);
                    console.log("Endpoint:", endpoint);
                    console.log("User data:", {
                        email: user.email,
                        name: user.name,
                        googleId: account.providerAccountId
                    });

                    // Django 백엔드 API 호출
                    const response = await axios.post(
                        endpoint,
                        {
                            email: user.email,
                            name: user.name,
                            image: user.image,
                            googleId: account.providerAccountId,
                        }
                    );

                    console.log("Backend response:", response.status);

                    // 백엔드에서 받은 정보를 user 객체에 추가
                    user.accessToken = response.data.tokens.access;
                    user.refreshToken = response.data.tokens.refresh;
                    user.isNewUser = response.data.isNewUser;
                    user.surveyCompleted = response.data.surveyCompleted;
                    user.userId = response.data.user.id;

                    console.log("Login successful:", {
                        email: user.email,
                        isNewUser: user.isNewUser,
                        surveyCompleted: user.surveyCompleted
                    });

                    return true;
                } catch (error) {
                    console.error("=== Login Error ===");
                    console.error("Error:", error);
                    if (axios.isAxiosError(error)) {
                        console.error("Response data:", error.response?.data);
                        console.error("Response status:", error.response?.status);
                        console.error("Request URL:", error.config?.url);
                        console.error("Request data:", error.config?.data);
                    }
                    return false;
                }
            }
            return true;
        },
        async jwt({ token, user }) {
            // Initial sign in - user 객체의 정보를 token에 저장
            if (user) {
                token.accessToken = user.accessToken;
                token.refreshToken = user.refreshToken;
                token.isNewUser = user.isNewUser;
                token.surveyCompleted = user.surveyCompleted;
                token.userId = user.userId;
                token.picture = user.image ?? token.picture;
            }
            return token;
        },
        async session({ session, token }) {
            // Session에 token 정보 전달
            if (session.user) {
                session.user.accessToken = token.accessToken as string;
                session.user.refreshToken = token.refreshToken as string;
                session.user.isNewUser = token.isNewUser as boolean;
                session.user.surveyCompleted = token.surveyCompleted as boolean;
                session.user.userId = token.userId as number;
                if (token.picture) {
                    session.user.image = token.picture as string;
                }
            }
            return session;
        },
        async redirect({ url, baseUrl }) {
            // 로그인 후 리다이렉트 처리
            // url에 callbackUrl 파라미터가 있으면 그곳으로, 없으면 /main으로
            if (url.startsWith("/")) return `${baseUrl}${url}`;
            else if (new URL(url).origin === baseUrl) return url;
            return `${baseUrl}/main`;
        },
    },
    pages: {
        signIn: '/login',
    }
});

export { handler as GET, handler as POST };
