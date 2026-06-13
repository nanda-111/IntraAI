import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessage from '../components/ChatMessage.vue'

describe('ChatMessage', () => {
  it('用户消息靠右显示，无头像', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'user', content: '你好' } },
    })
    expect(wrapper.find('.message.user').exists()).toBe(true)
    expect(wrapper.find('.avatar').exists()).toBe(false)
    expect(wrapper.find('.user-content').text()).toBe('你好')
  })

  it('AI 消息靠左显示，有头像', () => {
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
    expect(wrapper.find('.user-content').text()).toBe('**加粗**')
  })

  it('AI 消息经过 Markdown 渲染为 HTML', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'assistant', content: '**加粗**' } },
    })
    expect(wrapper.find('.content').html()).toContain('<strong>加粗</strong>')
  })

  it('有 reasoning 时显示思考面板', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'assistant',
          content: '回答',
          reasoning: '我在思考',
          reasoning_time: 3,
          reasoning_done: true,
          streaming: false,
        },
      },
    })
    expect(wrapper.find('.thinking-panel').exists()).toBe(true)
    expect(wrapper.find('.thinking-content').text()).toBe('我在思考')
  })

  it('无 reasoning 时不显示思考面板', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: { role: 'assistant', content: '回答' } },
    })
    expect(wrapper.find('.thinking-panel').exists()).toBe(false)
  })

  it('流式中显示思考中指示器', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'assistant',
          content: '',
          reasoning: null,
          streaming: true,
        },
      },
    })
    expect(wrapper.find('.thinking-panel').exists()).toBe(true)
    expect(wrapper.find('.thinking-spinner').exists()).toBe(true)
  })

  it('思考完成后显示 reasoning 内容和回答', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        message: {
          role: 'assistant',
          content: '这是回答',
          reasoning: '这是思考过程',
          reasoning_time: 5,
          reasoning_done: true,
          streaming: false,
        },
      },
    })
    expect(wrapper.find('.thinking-panel').exists()).toBe(true)
    expect(wrapper.find('.content').exists()).toBe(true)
    expect(wrapper.find('.content').html()).toContain('这是回答')
  })
})
