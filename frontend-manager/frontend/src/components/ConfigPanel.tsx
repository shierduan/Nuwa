/**
 * 配置面板组件
 */

import React, { useEffect, useState } from 'react'
import { useConfigStore } from '@/store/config'
import { ConfigInput } from './ConfigInput'
import { ConfigSection as ConfigSectionType } from '@/types/config'

export const ConfigPanel: React.FC = () => {
  const { config, originalConfig, isDirty, isLoading, error, loadConfig, updateConfig, resetConfig } = useConfigStore()
  const [activeSection, setActiveSection] = useState<string>('llm')
  const [sections, setSections] = useState<ConfigSectionType[]>([])

  // 加载配置
  useEffect(() => {
    if (Object.keys(config).length === 0) {
      loadConfig()
    }
  }, [])

  // 构建配置分组
  useEffect(() => {
    if (Object.keys(config).length === 0) return

    const sectionMap: Record<string, ConfigSectionType> = {
      llm: { name: 'llm', label: 'LLM配置', fields: [] },
      energy: { name: 'energy', label: '生物节律', fields: [] },
      memory: { name: 'memory', label: '记忆系统', fields: [] },
      cache: { name: 'cache', label: '缓存配置', fields: [] },
      system: { name: 'system', label: '系统设置', fields: [] }
    }

    // 配置项到分组的映射
    const fieldToSection: Record<string, string> = {
      llm_base_url: 'llm', llm_api_key: 'llm', llm_model_name: 'llm',
      llm_temperature: 'llm', llm_max_tokens: 'llm',
      energy_recovery_rate: 'energy', energy_consumption_base: 'energy',
      energy_consumption_system: 'energy', energy_critical_threshold: 'energy',
      memory_ttl_days: 'memory', memory_max_retrieval: 'memory',
      memory_emotion_weight: 'memory', cache_enabled: 'cache',
      cache_ttl: 'cache', cache_vector_maxsize: 'cache',
      cache_response_maxsize: 'cache', enable_heartbeat: 'system',
      enable_debug_mode: 'system', log_level: 'system'
    }

    Object.entries(config).forEach(([key, value]) => {
      const sectionKey = fieldToSection[key] || 'system'
      const section = sectionMap[sectionKey]
      
      if (section) {
        const type = typeof value === 'boolean' ? 'boolean' :
                     typeof value === 'number' ? 'number' :
                     typeof value === 'object' ? 'json' : 'string'
        
        section.fields.push({
          key,
          type,
          label: key.replace(/_/g, ' ').replace(/\b\w/g, s => s.toUpperCase()),
          value,
          default: originalConfig[key],
          description: getConfigDescription(key)
        })
      }
    })

    setSections(Object.values(sectionMap).filter(s => s.fields.length > 0))
  }, [config, originalConfig])

  const getConfigDescription = (key: string): string => {
    const descriptions: Record<string, string> = {
      llm_base_url: 'LLM服务地址',
      llm_api_key: 'API密钥',
      llm_model_name: '模型名称',
      llm_temperature: '温度参数 (0.0-1.0)',
      llm_max_tokens: '最大token数',
      energy_recovery_rate: '精力恢复速度',
      energy_consumption_base: '基础消耗',
      energy_consumption_system: '系统消耗',
      energy_critical_threshold: '临界阈值',
      memory_ttl_days: '记忆存活天数',
      cache_enabled: '启用缓存',
      enable_debug_mode: '调试模式'
    }
    return descriptions[key] || ''
  }

  const handleSave = async () => {
    // 收集变更
    const changes: Record<string, any> = {}
    for (const [key, value] of Object.entries(config)) {
      if (originalConfig[key] !== value) {
        changes[key] = value
      }
    }

    if (Object.keys(changes).length === 0) return

    try {
      await updateConfig(changes)
    } catch (error) {
      // 错误已在store中处理
    }
  }

  const handleReset = () => {
    resetConfig()
  }

  const handleInputChange = (key: string, value: any) => {
    useConfigStore.setState(state => ({
      config: { ...state.config, [key]: value }
    }))
  }

  if (isLoading && Object.keys(config).length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div className="config-panel space-y-6">
      {/* 错误提示 */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          错误: {error}
        </div>
      )}

      {/* 工具栏 */}
      <div className="flex justify-between items-center bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <div className="flex gap-2">
          {sections.map(section => (
            <button
              key={section.name}
              onClick={() => setActiveSection(section.name)}
              className={`px-4 py-2 rounded transition ${
                activeSection === section.name
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {section.label}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleReset}
            disabled={!isDirty}
            className="px-4 py-2 bg-gray-500 text-white rounded disabled:opacity-50 hover:bg-gray-600 transition"
          >
            重置
          </button>
          <button
            onClick={handleSave}
            disabled={!isDirty}
            className="px-4 py-2 bg-green-500 text-white rounded disabled:opacity-50 hover:bg-green-600 transition"
          >
            保存 {isDirty && '(*)'}
          </button>
        </div>
      </div>

      {/* 配置表单 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        {sections
          .filter(s => s.name === activeSection)
          .map(section => (
            <div key={section.name} className="space-y-4">
              <h3 className="text-lg font-semibold mb-4 pb-2 border-b dark:border-gray-700">
                {section.label}
              </h3>
              
              {section.fields.map(field => (
                <div key={field.key} className="flex flex-col gap-1">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {field.label}
                    {field.description && (
                      <span className="ml-2 text-xs text-gray-500 font-normal">
                        {field.description}
                      </span>
                    )}
                  </label>
                  <ConfigInput
                    field={field}
                    value={config[field.key]}
                    onChange={(value) => handleInputChange(field.key, value)}
                  />
                </div>
              ))}
            </div>
          ))}
      </div>
    </div>
  )
}
