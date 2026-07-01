/**
 * Axios 实例配置模块
 *
 * 【Axios 实例 vs 直接使用 axios 的区别】
 * - 直接使用 axios：需要每次请求都手动传入 baseURL、超时时间、请求头等配置，代码冗余且难以维护。
 * - 创建 axios 实例（axios.create）：可以预先设定统一的 baseURL、超时时间等默认配置，
 *   之后通过该实例发起的所有请求都会自动带上这些配置，实现"一次配置、全局复用"。
 *
 * 【请求拦截器的工作机制】
 * - 拦截器通过 api.interceptors.request.use(callback) 注册。
 * - 每次发起请求前，Axios 会自动调用拦截器回调函数，在请求真正发送前对其进行修改。
 * - 这里用于自动从 localStorage 中读取 token 并添加到请求头中，实现免手动携带认证信息。
 *
 * 【Bearer token 的含义】
 * - "Bearer" 是 HTTP 认证方案中的一种 token 类型标识，表示"持有者凭证"。
 * - 格式为：Authorization: Bearer <token>
 * - 服务端收到请求后，会解析 Bearer 后面的 token 来验证用户身份。
 * - 常用于 JWT（JSON Web Token）认证场景。
 *
 * 【401 处理的逻辑】
 * - 401 状态码表示"未授权"，通常意味着 token 过期或无效。
 * - 响应拦截器检测到 401 时，会自动清除本地存储的过期 token，
 *   并将页面跳转到 /login 让用户重新登录。
 * - 响应拦截器不直接弹出错误提示，以避免循环依赖问题，
 *   错误提示由各调用方自行处理。
 */
import axios from 'axios'

// 创建 Axios 实例，设置统一的基础配置
const api = axios.create({
  // 生产环境（Docker）中，一个域名下，前端和后端通过 Nginx 反向代理在同
  // 不需要指定后端地址（baseURL 为空，请求会发向当前域名）
  // 开发环境中，前端运行在 localhost:5173，后端在 localhost:8000，需要显式指定地址
  baseURL: import.meta.env.PROD ? '' : 'http://localhost:8000',
  timeout: 30000,                    // 请求超时时间：30 秒
})

// ==================== 请求拦截器 ====================
// 在每个请求发送前自动执行，用于注入认证 token
api.interceptors.request.use((config) => {
  // 从 localStorage 读取登录时保存的 token
  const token = localStorage.getItem('token')
  if (token) {
    // 将 token 以 Bearer 格式添加到 Authorization 请求头
    config.headers.Authorization = `Bearer ${token}`
  }
  return config // 必须返回 config，否则请求会被阻止
})

// ==================== 响应拦截器 ====================
// 在每个响应返回后自动执行，用于统一处理错误
api.interceptors.response.use(
  // 成功响应：直接返回，不做额外处理
  (res) => res,

  // 错误响应：统一处理
  (err) => {
    // 如果返回 401 状态码，说明 token 失效，需要重新登录
    if (err.response?.status === 401) {
      // 清除本地存储的过期 token
      localStorage.removeItem('token')
      // 自动跳转到登录页面
      window.location.href = '/login'
    }
    // 将错误继续向上抛出，由调用方（API 模块）决定如何展示错误信息
    // 注意：不在这里直接弹出 message 提示，以避免循环依赖问题
    return Promise.reject(err)
  }
)

export default api
