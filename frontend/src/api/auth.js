/**
 * 认证相关 API 模块
 *
 * 【为什么 API 要单独封装成模块】
 * 1. 关注点分离：将所有与后端通信的逻辑集中管理，与 UI 组件解耦。
 * 2. 复用性：同一个 API 可以在多个组件中调用，无需重复编写请求代码。
 * 3. 易维护：后端接口地址变更时，只需修改 API 模块中的路径，不用逐个修改组件。
 * 4. 可测试：API 模块可以单独进行单元测试。
 * 5. 统一管理：接口分类清晰（auth、knowledge 等），便于团队协作和后期扩展。
 */
import api from './index'

/**
 * 用户注册
 * @param {Object} data - 注册信息 { username, password }
 * @returns {Promise} Axios 请求 Promise
 */
export function register(data) {
  return api.post('/api/auth/register', data)
}

/**
 * 用户登录
 * @param {Object} data - 登录信息 { username, password }
 * @returns {Promise} Axios 请求 Promise，成功后返回包含 token 的响应
 */
export function login(data) {
  return api.post('/api/auth/login', data)
}

/**
 * 获取当前登录用户信息
 * 依赖请求拦截器自动携带 token（Bearer token 认证）
 * @returns {Promise} Axios 请求 Promise，返回当前用户信息
 */
export function getMe() {
  return api.get('/api/users/me')
}
