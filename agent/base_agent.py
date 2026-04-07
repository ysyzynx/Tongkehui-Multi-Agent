from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    """智能体抽象基类: 定义所有Agent必须实现的统一接口"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.context: Dict[str, Any] = {}
        self.result: Any = None
    
    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """执行智能体的核心业务逻辑，接受必要的参数，返回执行结果或者保存在self.result供后续调用"""
        pass
    
    def get_result(self) -> Any:
        """获取智能体执行结果"""
        return self.result
