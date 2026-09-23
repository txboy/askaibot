<template>
  <div class="not-found">
    <h1 class="code">404</h1>
    <p class="msg">页面不存在</p>
  </div>
</template>

<style scoped>
.not-found {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--bg);
}

.code {
  font-size: 72px;
  color: var(--text-muted);
  margin: 0;
}

.msg {
  color: var(--text-muted);
}
</style>
