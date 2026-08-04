# Frontend image for AI Pharmacy OS.
#
# Build context là GỐC REPO (cùng quy ước với infra/docker/backend.Dockerfile), để
# cả hai service build được từ cùng một context trong docker-compose:
#     podman build -f infra/docker/frontend.Dockerfile -t pharmacy-os-frontend .
#
# ⚠️ NEXT_PUBLIC_* bị Next.js đóng cứng vào bundle NGAY LÚC BUILD (`next build`),
# không đổi được sau đó bằng biến môi trường lúc container chạy — nên
# NEXT_PUBLIC_API_BASE_URL phải truyền qua --build-arg tại lúc build, không phải
# qua env_file như backend. Đổi domain/API base sau này ⇒ phải build lại image,
# không phải chỉnh compose rồi restart. (Chuẩn bị deploy AlmaLinux, 2026-08-04.)
FROM node:22-slim AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:22-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN npm run build

FROM node:22-slim AS run
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0
WORKDIR /app
# `output: "standalone"` (next.config.ts) copy đúng file server cần chạy, không cần
# `node_modules` đầy đủ hay `next start`. `.next/static`/`public` không nằm trong
# standalone theo mặc định — copy tay, đúng hướng dẫn chính thức của Next 16
# (node_modules/next/dist/docs/.../output.md, đã đọc trước khi viết theo AGENTS.md
# của frontend/ — bản Next này có thể khác quy ước đã biết).
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
