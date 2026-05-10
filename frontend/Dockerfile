# ============ 阶段 1：构建阶段 ============
# 使用 Node.js 镜像编译前端代码
# 【多阶段构建的优势】
# - 最终镜像只包含 Nginx 和编译后的静态文件，不包含 Node.js 运行时和源代码
# - 镜像体积大幅缩小（从数百 MB 缩小到几十 MB）
# - 生产环境攻击面更小，安全性更高
FROM node:18-alpine AS build

WORKDIR /app

# 先复制 package 文件，利用 Docker 层缓存
# 如果 package.json 没有变化，npm install 这一层会被缓存，不会重新执行
COPY package*.json ./
RUN npm install

# 复制源代码并构建
COPY . .
RUN npm run build

# ============ 阶段 2：运行阶段 ============
# 使用 Nginx 托管静态文件
# 这个阶段不包含 Node.js、源代码等，只有编译产物和 Nginx
FROM nginx:alpine

# 从构建阶段复制编译产物到 Nginx 的默认静态文件目录
COPY --from=build /app/dist /usr/share/nginx/html

# 复制自定义 Nginx 配置，替换默认配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
