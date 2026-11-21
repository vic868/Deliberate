```python
# 导入项目中的全局配置对象 settings
# 一般 settings 里面会包含 default_model、API Key、Base URL 等配置
from app.core.config import settings

# 导入 LLM Provider 的抽象基类 / 父类
# DeepSeekProvider、OpenAIProvider、QwenProvider 都应该继承它
from app.llm.base import BaseLLMProvider

# 导入三个具体的大模型 Provider 实现
from app.llm.providers import DeepSeekProvider, OpenAIProvider, QwenProvider

# 导入 Provider 名称枚举
# 例如可能定义了：
# DEEPSEEK = "deepseek"
# QWEN = "qwen"
# OPENAI = "openai"
from app.llm.schemas import LLMProviderName


# 定义一个 LLM Provider 工厂类
# 作用：统一负责创建不同厂商对应的 Provider 对象
class LLMProviderFactory:

    # staticmethod 表示这是一个静态方法
    # 调用时不需要先创建 LLMProviderFactory 对象
    # 可以直接：
    # LLMProviderFactory.create()
    @staticmethod
    def create(
        # provider 可以传：
        # 1. LLMProviderName 枚举
        # 2. 字符串，例如 "deepseek"
        # 3. None，表示没有指定
        provider: LLMProviderName | str | None = None
    ) -> BaseLLMProvider:
        # 如果调用方传了 provider，就直接使用
        #
        # 如果 provider 是 None，
        # 就根据 settings.default_model 自动推断 Provider
        #
        # 例如：
        # settings.default_model = "deepseek-chat"
        # infer_provider_from_model(...) 会返回 DEEPSEEK
        provider_name = provider or infer_provider_from_model(
            settings.default_model
        )

        # 如果 provider_name 是字符串
        # 例如：
        # "deepseek"
        #
        # 就把它转换成 LLMProviderName 枚举
        #
        # 相当于：
        # LLMProviderName("deepseek")
        # =>
        # LLMProviderName.DEEPSEEK
        if isinstance(provider_name, str):
            provider_name = LLMProviderName(provider_name)

        # 判断 Provider 是否是 DeepSeek
        if provider_name == LLMProviderName.DEEPSEEK:
            # 创建并返回 DeepSeekProvider 对象
            return DeepSeekProvider()

        # 判断 Provider 是否是 Qwen
        if provider_name == LLMProviderName.QWEN:
            # 创建并返回 QwenProvider 对象
            return QwenProvider()

        # 判断 Provider 是否是 OpenAI
        if provider_name == LLMProviderName.OPENAI:
            # 创建并返回 OpenAIProvider 对象
            return OpenAIProvider()

        # 如果传进来的 Provider 不在支持范围内
        # 直接抛出 ValueError
        raise ValueError(
            f"不支持的 LLM Provider：{provider_name}"
        )


# 定义一个辅助函数
# 作用：
# 根据模型名称自动判断这个模型属于哪个 Provider
def infer_provider_from_model(model: str) -> LLMProviderName:

    # 如果模型名称以 deepseek 开头
    #
    # 例如：
    # deepseek-chat
    # deepseek-reasoner
    #
    # 就认为它属于 DeepSeek
    if model.startswith("deepseek"):
        return LLMProviderName.DEEPSEEK

    # 如果模型名称以 qwen 开头
    #
    # 例如：
    # qwen-plus
    # qwen-max
    #
    # 就认为属于 Qwen
    if model.startswith("qwen"):
        return LLMProviderName.QWEN

    # 如果模型名称以 gpt 开头
    #
    # 例如：
    # gpt-4o
    # gpt-5
    #
    # 就认为属于 OpenAI
    if model.startswith("gpt"):
        return LLMProviderName.OPENAI

    # 如果前面的规则都匹配不上
    # 默认兜底使用 DeepSeek
    return LLMProviderName.DEEPSEEK
```
