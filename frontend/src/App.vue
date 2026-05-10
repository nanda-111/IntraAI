<!--
  App.vue — 应用根组件

  使用 <router-view /> 作为路由出口：
  Vue Router 会根据当前 URL 路径，将匹配到的页面组件渲染在这里。
  例如：
  - 访问 /login → 渲染 LoginView
  - 访问 / → 渲染 ChatView
  - 访问 /knowledge → 渲染 KnowledgeView
-->
<template>
  <router-view />
</template>
