import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessage from '../components/ChatMessage.vue'

describe('ChatMessage', () => {
  it('用户消息靠右显示，显示"我"头像', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'user', content: '你好' } },
    })
    expect(wrapper.find('.message.user').exists()).toBe(true)
    expect(wrapper.find('.avatar').text()).toBe('我')
  })

  it('AI 消息靠左显示，显示"AI"头像', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'assistant', content: '你好！' } },
    })
    expect(wrapper.find('.message.assistant').exists()).toBe(true)
    expect(wrapper.find('.avatar').text()).toBe('AI')
  })

  it('用户消息不经过 Markdown 渲染', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'user', content: '**加粗**' } },
    })
    expect(wrapper.find('.content').text()).toBe('**加粗**')
  })

  it('AI 消息经过 Markdown 渲染为 HTML', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'assistant', content: '**加粗**' } },
    })
    expect(wrapper.find('.content').html()).toContain('<strong>加粗</strong>')
  })
})
