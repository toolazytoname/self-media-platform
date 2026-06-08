import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

// Design system tokens (Apple + Claude) — load BEFORE our overrides
import './styles/tokens.css'
import './styles/typography.css'
import './styles/el-overrides.css'
import './styles/app-shell.css'
import './styles/components.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')