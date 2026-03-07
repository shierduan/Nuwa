/**
 * 配置输入组件 - 根据类型渲染不同输入控件
 */

import React, { useState } from 'react'
import { ConfigField } from '@/types/config'

interface ConfigInputProps {
  field: ConfigField
  value: any
  onChange: (value: any) => void
}

export const ConfigInput: React.FC<ConfigInputProps> = ({ field, value, onChange }) => {
  const [jsonError, setJsonError] = useState<string | null>(null)

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const val = e.target.value
    onChange(val)
  }

  const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value)
    if (!isNaN(val)) {
      onChange(val)
    }
  }

  const handleBooleanChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.checked)
  }

  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value
    try {
      JSON.parse(val)
      setJsonError(null)
      onChange(val)
    } catch (error) {
      setJsonError('JSON格式错误')
    }
  }

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange(e.target.value)
  }

  // String input
  if (field.type === 'string') {
    return (
      <input
        type="text"
        value={value || ''}
        onChange={handleTextChange}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder={field.default?.toString() || ''}
      />
    )
  }

  // Number input
  if (field.type === 'number') {
    return (
      <div className="flex gap-2 items-center">
        <input
          type="number"
          value={value}
          onChange={handleNumberChange}
          className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          step="any"
        />
        {field.validation?.min !== undefined && (
          <span className="text-xs text-gray-500">min: {field.validation.min}</span>
        )}
        {field.validation?.max !== undefined && (
          <span className="text-xs text-gray-500">max: {field.validation.max}</span>
        )}
      </div>
    )
  }

  // Boolean input (toggle switch)
  if (field.type === 'boolean') {
    return (
      <label className="flex items-center cursor-pointer">
        <div className="relative">
          <input
            type="checkbox"
            checked={value || false}
            onChange={handleBooleanChange}
            className="sr-only"
          />
          <div
            className={`block w-14 h-8 rounded-full transition ${
              value ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
            }`}
          ></div>
          <div
            className={`absolute left-1 top-1 w-6 h-6 bg-white rounded-full transition transform ${
              value ? 'translate-x-6' : ''
            }`}
          ></div>
        </div>
        <span className="ml-3 text-sm font-medium">
          {value ? '已启用' : '已禁用'}
        </span>
      </label>
    )
  }

  // Select input
  if (field.type === 'select' && field.options) {
    return (
      <select
        value={value}
        onChange={handleSelectChange}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {field.options.map(option => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    )
  }

  // JSON input
  if (field.type === 'json') {
    const displayValue = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
    
    return (
      <div className="space-y-1">
        <textarea
          value={displayValue}
          onChange={handleJsonChange}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={4}
          placeholder='{"key": "value"}'
        />
        {jsonError && (
          <span className="text-xs text-red-500">{jsonError}</span>
        )}
      </div>
    )
  }

  // Default text input
  return (
    <input
      type="text"
      value={value || ''}
      onChange={handleTextChange}
      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  )
}
