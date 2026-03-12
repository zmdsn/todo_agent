# tests/test_estimator.py
from todo_mcp.utils.estimator import TaskEstimator


def test_estimate_simple_task():
    """测试简单任务预估"""
    estimator = TaskEstimator()
    result = estimator.estimate("回复邮件")

    assert result["estimated_minutes"] > 0
    assert result["should_split"] == False


def test_estimate_complex_task():
    """测试复杂任务预估"""
    estimator = TaskEstimator()
    result = estimator.estimate("完成季度报告，包括数据收集、分析和撰写")

    assert result["estimated_minutes"] > 120
    assert result["should_split"] == True


def test_estimate_with_priority():
    """测试优先级影响预估"""
    estimator = TaskEstimator()

    low_result = estimator.estimate("写代码", priority="low")
    high_result = estimator.estimate("写代码", priority="high")

    # 高优先级任务预估时间应该更长
    assert high_result["estimated_minutes"] > low_result["estimated_minutes"]


def test_split_task():
    """测试任务拆分"""
    estimator = TaskEstimator()
    result = estimator.split("完成季度报告，包括数据收集、分析和撰写", target_minutes=60)

    assert len(result["subtasks"]) >= 2
    assert all(s["estimated_minutes"] <= 90 for s in result["subtasks"])
    assert result["total_minutes"] > 0
