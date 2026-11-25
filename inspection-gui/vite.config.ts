import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { apiProxy } from './apiProxy'
import {mvApiBridge} from './mvApiBridge.mjs'

export default defineConfig(({mode})=>{
  const env=loadEnv(mode,'.','')
  const proxy=apiProxy(env.GUI_API_TARGET??'http://127.0.0.1:8080')
  return {
    plugins:[react(),mvApiBridge()],
    server:{proxy},
    preview:{proxy},
    test:{environment:'node',include:['src/**/*.test.ts'],css:{include:[/tokens\.css/]}} ,
  }
})
