<script setup>
import { computed } from 'vue'

const props = defineProps({
  provider: { type: String, default: 'feishu' },
  redirect: { type: String, default: '' },
})

const paths = {
  feishu: '/api/auth/feishu/callback',
  dingtalk: '/api/auth/dingtalk/callback',
  wecom: '/api/auth/wecom/callback',
}

const callback = computed(() => {
  const base = (props.redirect || 'https://your.domain').replace(/\/+$/, '')
  return base + (paths[props.provider] || '')
})
</script>

<template>
  <details class="login-guide">
    <summary>申请凭证与配置回调地址（含常见错误）</summary>
    <div class="guide">
      <template v-if="provider === 'feishu'">
        <p>
          <b>1. 申请凭证</b>：登录
          <a href="https://open.feishu.cn" target="_blank" rel="noopener">飞书开放平台</a>
          ，创建「企业自建应用」，在「凭证与基础信息」复制 <code>App ID</code>（<code>cli_</code> 开头）和 <code>App Secret</code>。
        </p>
        <p>
          <b>2. 开通登录</b>：应用「权限管理」添加登录相关权限（如 <code>user_info</code>），并「创建版本并发布」，发布后组织成员才能登录。
        </p>
        <p><b>3. 配置回调地址</b>：应用「安全设置 → 重定向 URL」填入：</p>
        <pre class="code">{{ callback }}</pre>
        <p>
          <b>4. 常见错误</b>：若收到
          <code>错误码 20029「重定向 URL 有误」</code>，说明开放平台「重定向 URL」与本页回调地址不一致。请确保两端<b>逐字一致</b>（含协议、域名、端口及子路径，不要多/少尾部斜杠）。
        </p>
      </template>

      <template v-else-if="provider === 'dingtalk'">
        <p>
          <b>1. 申请凭证</b>：登录
          <a href="https://open.dingtalk.com" target="_blank" rel="noopener">钉钉开放平台</a>
          ，创建应用，在「凭证与基础信息」复制 <code>AppKey</code>（Client ID）、<code>AppSecret</code>（Client Secret）与 <code>AgentId</code>。
        </p>
        <p><b>2. 开通登录</b>：应用添加「登录 / 扫码登录」相关权限并发布上线。</p>
        <p><b>3. 配置回调地址</b>：应用「登录与分享 / OAuth」配置「回调地址（redirect_uri）」：</p>
        <pre class="code">{{ callback }}</pre>
        <p>
          <b>4. 常见错误</b>：若提示「redirect_uri 不合法 / 回调地址不一致」，请核对钉钉开放平台「回调域名」与本页「回调域名」一致，且提交的 redirect_uri 为上面的完整回调。
        </p>
      </template>

      <template v-else-if="provider === 'wecom'">
        <p>
          <b>1. 申请凭证</b>：登录
          <a href="https://work.weixin.qq.com" target="_blank" rel="noopener">企业微信管理后台</a>
          ，应用管理 → 创建「自建应用」，复制 <code>CorpID</code>（我的企业 → 企业信息）、应用 <code>Secret</code> 与 <code>AgentId</code>。
        </p>
        <p><b>2. 开通网页授权</b>：应用「网页授权及 JS-SDK」设置「可信域名」。</p>
        <p><b>3. 配置回调地址</b>：在「企业微信授权登录 / 网页授权」中设置授权回调域名，使回调为：</p>
        <pre class="code">{{ callback }}</pre>
        <p>
          <b>4. 常见错误</b>：若提示「appid / redirect_uri 不匹配」或无法跳转，请确认「可信域名 / 授权回调域名」与本页「回调域名」一致。
        </p>
      </template>
    </div>
  </details>
</template>

<style scoped>
.login-guide {
  margin-top: 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-soft);
  padding: 10px 12px;
}

.login-guide summary {
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.guide {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-muted);
}

.guide p {
  margin: 0;
}

.code {
  background: var(--bg-sidebar);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  font-family: monospace;
  color: var(--primary);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.guide a {
  color: var(--primary);
}

.guide code {
  background: var(--bg-sidebar);
  padding: 1px 4px;
  border-radius: 4px;
}
</style>
