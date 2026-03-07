import aiohttp
import asyncio
from typing import Dict, Any, Optional

async def web_fetch(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    网页抓取工具函数
    
    Args:
        params: 包含url等参数的字典
        
    Returns:
        包含抓取结果的字典
    """
    url = params.get('url')
    if not url:
        return {
            'success': False,
            'message': '缺少URL参数',
            'data': None
        }
    
    try:
        # 确保URL格式正确
        if not url.startswith('http'):
            url = 'https://' + url
        
        # 设置超时时间
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }) as response:
                # 读取响应内容
                content = await response.text()
                
                # 提取标题
                title = ''
                import re
                title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                
                # 提取描述
                description = ''
                desc_match = re.search(r'<meta name="description" content="(.*?)"', content, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1).strip()
                
                # 提取主要内容（简单实现）
                main_content = ''
                # 移除脚本和样式
                content_clean = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL)
                content_clean = re.sub(r'<style.*?</style>', '', content_clean, flags=re.DOTALL)
                # 提取<p>标签内容
                p_matches = re.findall(r'<p>(.*?)</p>', content_clean, re.DOTALL)
                if p_matches:
                    main_content = '\n'.join([p.strip() for p in p_matches[:5]])  # 只取前5个段落
                
                return {
                    'success': True,
                    'message': f'成功抓取 {url}',
                    'data': {
                        'url': url,
                        'status': response.status,
                        'title': title,
                        'description': description,
                        'content': main_content[:1000]  # 限制内容长度
                    }
                }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'抓取失败: {str(e)}',
            'data': None
        }

async def search_web(query: str, engine: str = 'google') -> Dict[str, Any]:
    """
    使用搜索引擎搜索
    
    Args:
        query: 搜索关键词
        engine: 搜索引擎名称
        
    Returns:
        搜索结果
    """
    # 搜索引擎URL模板
    engines = {
        'google': 'https://www.google.com/search?q={query}',
        'baidu': 'https://www.baidu.com/s?wd={query}',
        'bing': 'https://cn.bing.com/search?q={query}',
        'duckduckgo': 'https://duckduckgo.com/html/?q={query}'
    }
    
    # 获取搜索引擎URL
    engine_url = engines.get(engine, engines['google'])
    url = engine_url.format(query=query.replace(' ', '+'))
    
    # 调用web_fetch
    result = await web_fetch({'url': url})
    
    # 解析搜索结果
    if result['success']:
        content = result['data']['content']
        # 提取搜索结果（简单实现）
        search_results = []
        # 这里需要根据不同搜索引擎的HTML结构进行解析
        # 简单实现，仅作为示例
        search_results.append({
            'title': result['data']['title'],
            'url': url,
            'description': result['data']['description']
        })
        
        result['data']['search_results'] = search_results
    
    return result
