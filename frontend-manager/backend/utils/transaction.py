"""
事务管理工具

提供事务管理和回滚支持
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class Transaction:
    """事务数据类"""
    
    id: str
    timestamp: datetime
    operation: str
    data: Dict[str, Any]
    old_values: Dict[str, Any]
    status: str = "pending"  # pending, committed, rolled_back, failed
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "data": self.data,
            "old_values": self.old_values,
            "status": self.status,
        }


class TransactionManager:
    """事务管理器"""
    
    def __init__(self):
        self.transactions: List[Transaction] = []
        self._max_history = 100
    
    def create(self, operation: str, data: Dict[str, Any], old_values: Dict[str, Any]) -> Transaction:
        """创建事务"""
        txn = Transaction(
            id=f"txn_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            operation=operation,
            data=data,
            old_values=old_values
        )
        self.transactions.append(txn)
        
        # 限制历史记录
        if len(self.transactions) > self._max_history:
            self.transactions = self.transactions[-self._max_history:]
        
        return txn
    
    def commit(self, txn: Transaction):
        """提交事务"""
        txn.status = "committed"
    
    def rollback(self, txn: Transaction):
        """回滚事务"""
        txn.status = "rolled_back"
    
    def fail(self, txn: Transaction, error: str):
        """标记失败"""
        txn.status = "failed"
        txn.error = error  # type: ignore
    
    def get_by_id(self, txn_id: str) -> Optional[Transaction]:
        """根据ID获取事务"""
        for txn in self.transactions:
            if txn.id == txn_id:
                return txn
        return None
    
    def get_recent(self, limit: int = 20) -> List[Transaction]:
        """获取最近的事务"""
        return self.transactions[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total": len(self.transactions),
            "committed": sum(1 for t in self.transactions if t.status == "committed"),
            "rolled_back": sum(1 for t in self.transactions if t.status == "rolled_back"),
            "failed": sum(1 for t in self.transactions if t.status == "failed"),
            "pending": sum(1 for t in self.transactions if t.status == "pending"),
        }
        return stats


__all__ = ["Transaction", "TransactionManager"]
