<!--
  登录/注册页面 — IntraAI 应用的入口页面
  用户首次打开应用时，如果未登录，会被路由守卫重定向到此页面

  【Ant Design Vue 组件说明】
  - a-card: 卡片容器，提供标题栏和阴影效果，让表单看起来更整洁
  - a-form: 表单组件，提供数据绑定、校验、提交等完整功能
  - a-form-item: 表单项组件，包含 label（标签）、校验规则、错误提示
  - a-input: 普通文本输入框
  - a-input-password: 密码输入框，自带显示/隐藏密码的切换按钮
  - a-button: 按钮组件，支持 type（样式）、loading（加载状态）、block（占满宽度）
-->
<template>
  <!-- 登录容器：全屏居中布局 -->
  <div class="login-container">
    <!--
      a-card 卡片组件
      - :title 动态绑定标题，根据 isLogin 切换"登录"或"注册"
      - isLogin ? '登录 IntraAI' : '注册 IntraAI' 是三元表达式
    -->
    <a-card
      class="login-card"
      :title="isLogin ? '登录 IntraAI' : '注册 IntraAI'"
    >
      <!--
        a-form 表单组件

        【:model="form" 的作用】
        将表单的数据模型绑定到 form 响应式对象。
        当用户在输入框中输入内容时，form 对象的对应属性会自动更新（双向绑定）。
        提交时，a-form 可以从 form 对象中获取所有字段的值。

        【@finish 事件】
        @finish 是 a-form 组件的特有事件，不是原生 HTML 事件。
        区别于 @click（按钮点击事件）：
        - @click：绑定在按钮上，用户点击按钮时触发，不关心表单校验
        - @finish：绑定在 a-form 上，只有当所有表单校验规则通过后才触发
        这意味着 @finish 回调被调用时，表单数据已经通过了所有 rules 校验，可以直接使用。

        【layout="vertical"】
        表单布局方式，"vertical" 表示标签在输入框上方（垂直排列）
        其他选项：horizontal（标签在左侧，水平排列）、inline（所有项在同一行）
      -->
      <a-form
        :model="form"
        layout="vertical"
        @finish="handleSubmit"
      >
        <!--
          用户名输入项

          【a-form-item 的核心属性】
          - label: 显示在输入框上方的文字标签
          - name: 字段名，必须与 form 对象中的属性名一致，用于校验和数据绑定
          - :rules: 校验规则数组，每条规则是一个对象

          【rules 校验机制详解】
          rules 是一个数组，包含多个校验规则对象。每条规则可以有：
          - required: 是否必填，true 时如果字段为空会显示校验错误
          - message: 校验失败时显示的错误提示文字
          - min/max: 字符串最小/最大长度
          - pattern: 正则表达式校验（如 pattern: /^.+@.+$/ 校验邮箱格式）
          - type: 数据类型校验（如 type: 'email' 校验邮箱格式）
          - validator: 自定义校验函数，可以实现任意复杂的校验逻辑

          校验触发时机（默认值通常足够）：
          - change: 输入框内容变化时校验
          - blur: 输入框失去焦点时校验
          - submit: 表单提交时校验

          a-form 会按顺序执行所有规则，只要有一条规则不通过，就停止后续校验并显示错误信息。
        -->
        <a-form-item
          label="用户名"
          name="username"
          :rules="[{ required: true, message: '请输入用户名' }]"
        >
          <!--
            a-input: 普通文本输入框
            v-model:value="form.username" 双向绑定：
            - 用户输入内容 → form.username 自动更新
            - 代码修改 form.username → 输入框自动更新
            placeholder: 输入框为空时的灰色提示文字
          -->
          <a-input
            v-model:value="form.username"
            placeholder="请输入用户名"
          />
        </a-form-item>

        <!--
          邮箱输入项 — 仅在注册模式下显示（!isLogin 表示"非登录"即注册）

          【v-if 条件渲染】
          v-if 是 Vue 的条件渲染指令：
          - 条件为 true 时：DOM 元素被创建并插入页面
          - 条件为 false 时：DOM 元素从页面完全移除（不是隐藏，是不存在）
          区别于 v-show：v-show 只是 display: none 隐藏，元素仍在 DOM 中
          这里用 v-if 是因为登录时不需要邮箱字段，注册表单完全移除它更合理。
        -->
        <a-form-item
          v-if="!isLogin"
          label="邮箱"
          name="email"
          :rules="[{ required: true, message: '请输入邮箱' }]"
        >
          <a-input
            v-model:value="form.email"
            placeholder="请输入邮箱"
          />
        </a-form-item>

        <!--
          密码输入项
          a-input-password 自带眼睛图标，可以切换密码的显示/隐藏
        -->
        <a-form-item
          label="密码"
          name="password"
          :rules="[{ required: true, message: '请输入密码' }]"
        >
          <a-input-password
            v-model:value="form.password"
            placeholder="请输入密码"
          />
        </a-form-item>

        <!--
          提交按钮

          【html-type="submit"】
          告诉 a-button 扮演 HTML 原生 <button type="submit"> 的角色。
          当用户点击此按钮时，会触发所属 a-form 的 @finish 事件（前提是校验通过）。
          如果不加 html-type="submit"，点击按钮不会触发表单提交，需要手动用 @click 处理。

          【:loading="loading"】
          loading 为 true 时，按钮显示加载动画（旋转图标），同时按钮变为不可点击状态。
          这是一种防止用户重复提交的简单有效方式。

          【block】
          block 是 Ant Design Vue 的属性，让按钮宽度占满父容器（100% width）。
        -->
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            :loading="loading"
            block
          >
            {{ isLogin ? '登录' : '注册' }}
          </a-button>
        </a-form-item>

        <!--
          切换登录/注册模式的链接
          @click 是 Vue 的事件绑定语法，点击时执行后面的表达式

          【@click vs @finish 的区别】
          - @click：绑定在普通 DOM 元素或组件上，用户点击时立即触发
          - @finish：绑定在 a-form 上，只有所有 rules 校验通过后才触发
          这里用 @click 是因为切换模式不需要校验，只是一个简单的布尔值翻转操作。

          【isLogin = !isLogin】
          这是一个取反赋值操作：
          - isLogin 当前为 true → 点击后变为 false（显示注册表单）
          - isLogin 当前为 false → 点击后变为 true（显示登录表单）
          因为 isLogin 是 ref 包装的响应式变量，Vue 会自动检测到变化并更新 DOM。
        -->
        <a
          style="text-align: center; display: block; cursor: pointer"
          @click="isLogin = !isLogin"
        >
          {{ isLogin ? '没有账号？去注册' : '已有账号？去登录' }}
        </a>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
/**
 * <script setup> — Vue 3 组合式 API 的语法糖
 * - 顶层声明的变量、函数自动暴露给模板使用
 * - 无需手动 return、无需 setup() 函数包裹
 * - 是 Vue 3 + Vite 项目的推荐写法
 */

// ===== 导入依赖 =====

/**
 * ref：创建基本类型的响应式变量（字符串、数字、布尔值等）
 * reactive：创建对象类型的响应式变量（对象、数组）
 *
 * 【ref vs reactive 的使用场景】
 *
 * ref 的特点：
 * 1. 可以包装任何类型的值（基本类型、对象、数组都行）
 * 2. 在 JavaScript 中读写需要通过 .value（如 isLogin.value = false）
 * 3. 在模板 <template> 中会自动解包，不需要 .value（直接写 isLogin 即可）
 * 4. 适合用于：单个基本类型值、需要整体替换的值
 *
 * reactive 的特点：
 * 1. 只能包装对象类型（对象、数组），不能包装基本类型
 * 2. 自动深层响应式，访问属性不需要 .value（直接写 form.username）
 * 3. 适合用于：表单数据、有多个属性需要分别修改的对象
 *
 * 本文件中的选择：
 * - isLogin（布尔值）→ ref：基本类型，只能用 ref
 * - loading（布尔值）→ ref：基本类型，只能用 ref
 * - form（对象 { username, email, password }）→ reactive：
 *   它是一个多属性对象，各个属性需要分别读写，用 reactive 更自然
 */
import { ref, reactive } from 'vue'

/**
 * useRouter：获取路由实例，用于编程式导航（跳转页面）
 * 使用场景：在 JavaScript 代码中控制页面跳转（而非 <router-link> 标签跳转）
 */
import { useRouter } from 'vue-router'

/**
 * message：Ant Design Vue 的全局消息提示 API
 * 使用场景：操作成功/失败时显示一个短暂的提示框
 * - message.success('内容')：绿色成功提示
 * - message.error('内容')：红色错误提示
 * - message.info('内容')：蓝色信息提示
 */
import { message } from 'ant-design-vue'

/**
 * useAuthStore：从认证 Store 中获取状态和方法
 * 返回的是一个 Store 实例，包含：token、user、login、register 等
 */
import { useAuthStore } from '../stores/auth'

// ===== 初始化 =====

// 获取路由实例，用于登录成功后跳转到首页
const router = useRouter()

// 获取认证 Store 实例，用于调用 login() 和 register() 方法
const authStore = useAuthStore()

// ===== 响应式状态 =====

/**
 * isLogin：控制显示登录表单还是注册表单
 * - true → 显示登录表单（只有用户名和密码）
 * - false → 显示注册表单（有用户名、邮箱和密码）
 *
 * 用 ref 包装布尔值：
 * - 在 JavaScript 中读写：isLogin.value = true
 * - 在模板中自动解包：直接用 isLogin（不需要 .value）
 */
const isLogin = ref(true)

/**
 * loading：控制按钮的加载状态
 * - true → 按钮显示加载动画，不可点击（防止重复提交）
 * - false → 按钮正常状态
 *
 * 防重复提交的意义：
 * 用户点击登录后，如果网络较慢，可能会再次点击。
 * 如果没有 loading 保护，会发送多次请求，可能导致：
 * 1. 服务器压力增大
 * 2. 用户收到多条"登录成功"消息
 * 3. 竞态条件导致状态不一致
 */
const loading = ref(false)

/**
 * form：表单数据对象
 * 使用 reactive 创建深层响应式对象。
 *
 * reactive 的工作原理：
 * - 对 form 的任何属性读写都会自动触发响应式更新
 * - form.username = 'test' → Vue 自动更新绑定的 a-input
 * - 用户在 a-input 中输入 → form.username 自动更新
 *
 * 注意：reactive 对象不能解构，否则会失去响应式：
 *   const { username } = form  // ❌ username 不再是响应式的
 *   const username = form.username  // ✅ 保持响应式
 */
const form = reactive({
  username: '',  // 用户名
  email: '',     // 邮箱（仅注册时使用）
  password: ''   // 密码
})

// ===== 方法 =====

/**
 * 处理表单提交
 *
 * 【这个函数什么时候被调用？】
 * 当用户点击"登录"或"注册"按钮时：
 * 1. 按钮是 html-type="submit"，点击后触发所属 a-form 的提交
 * 2. a-form 首先执行所有 rules 校验
 * 3. 只有所有校验通过后，才触发 @finish 事件 → 调用 handleSubmit()
 *
 * 【为什么用 try/finally 而不是 try/catch？】
 *
 * try/catch 的模式：
 *   try { ... } catch(e) { loading.value = false }
 *   - 只有发生异常时才执行 catch
 *   - 如果 try 正常执行完毕，catch 不执行
 *   - 需要在 try 正常结束处也写 loading.value = false
 *
 * try/finally 的模式（本文件使用）：
 *   try { ... } finally { loading.value = false }
 *   - 不管 try 是正常完成还是抛出异常，finally 都会执行
 *   - 确保 loading 状态一定会被重置为 false
 *   - 避免因异常导致按钮永远处于 loading 状态（用户无法再次操作）
 *
 * 【异常如何处理？】
 * handleSubmit 没有 try/catch，异常会向上冒泡。
 * Ant Design Vue 的 a-form 会自动捕获 @finish 中的异常并显示错误提示。
 * 同时，axios 拦截器（在 src/api/axios.js 中）也会处理网络错误并显示 message.error。
 * 因此这里不需要手动 catch，避免重复处理异常。
 */
async function handleSubmit() {
  // 开启 loading，按钮进入加载状态，防止重复提交
  loading.value = true

  try {
    if (isLogin.value) {
      /**
       * 登录流程：
       * 1. 调用 authStore.login() → 内部调用后端登录 API
       * 2. 保存 token 和用户信息到 Store（详见 auth.js）
       * 3. 显示成功提示
       * 4. 使用 router.push('/') 跳转到首页
       *
       * router.push 的参数：
       * - '/' 是目标路径（首页）
       * - 也可以用命名路由：router.push({ name: 'home' })
       * - 登录后跳转到首页是常见的 UX 设计
       */
      await authStore.login({ username: form.username, password: form.password })
      message.success('登录成功')
      router.push('/')
    } else {
      /**
       * 注册流程：
       * 1. 调用 authStore.register() → 内部调用后端注册 API
       * 2. 注册成功后不自动登录（这是安全设计，详见 auth.js 注释）
       * 3. 切换到登录表单，让用户手动登录
       *
       * form 对象包含 { username, email, password }
       * 三个属性都通过 v-model:value 双向绑定到输入框
       * 用户填写的信息会自动同步到 form 对象中
       */
      await authStore.register(form)
      message.success('注册成功，请登录')
      isLogin.value = true
    }
  } finally {
    /**
     * finally 块：不管 try 中是成功还是抛出异常，都会执行
     * 确保 loading 状态被重置，按钮恢复可点击状态
     */
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #1a1a2e;
}

.login-card {
  width: 400px;
  border-radius: 12px;
}

.login-card :deep(.ant-card-head-title) {
  font-size: 20px;
  font-weight: 600;
}

.login-card :deep(.ant-btn-primary) {
  background: #4D6BFE;
  border-color: #4D6BFE;
}

.login-card :deep(.ant-btn-primary:hover) {
  background: #3d5be0;
  border-color: #3d5be0;
}

.login-card :deep(a) {
  color: #4D6BFE;
}
</style>
