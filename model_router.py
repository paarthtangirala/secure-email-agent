#!/usr/bin/env python3
"""
Model Router - Dynamic LLM model selection for optimal cost/performance
Part of MailMaestro-level intelligence layer
"""

import time
from typing import Dict, List, Optional
from enum import Enum

class ModelType(Enum):
    """Available model types"""
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o" 
    GEMINI_FLASH = "gemini-1.5-flash"
    CLAUDE_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"

class TaskType(Enum):
    """Task types for model routing"""
    SUMMARIZE = "summarize"
    DRAFT = "draft" 
    TASKS = "tasks"
    CLASSIFY = "classify"
    EXTRACT = "extract"
    TRANSLATE = "translate"
    ANALYZE = "analyze"

class ModelRouter:
    """Route tasks to optimal models based on cost, speed, and quality requirements"""
    
    def __init__(self):
        self.model_configs = {
            ModelType.GPT_4O_MINI: {
                "cost_per_1k_tokens": 0.00015,  # Input
                "speed_score": 9,  # 1-10 scale
                "quality_score": 7,
                "context_limit": 128000,
                "provider": "openai"
            },
            ModelType.GPT_4O: {
                "cost_per_1k_tokens": 0.005,
                "speed_score": 6,
                "quality_score": 9,
                "context_limit": 128000,
                "provider": "openai"
            },
            ModelType.GEMINI_FLASH: {
                "cost_per_1k_tokens": 0.000075,
                "speed_score": 10,
                "quality_score": 7,
                "context_limit": 1000000,
                "provider": "google"
            },
            ModelType.CLAUDE_HAIKU: {
                "cost_per_1k_tokens": 0.00025,
                "speed_score": 8,
                "quality_score": 6,
                "context_limit": 200000,
                "provider": "anthropic"
            },
            ModelType.CLAUDE_SONNET: {
                "cost_per_1k_tokens": 0.003,
                "speed_score": 7,
                "quality_score": 9,
                "context_limit": 200000,
                "provider": "anthropic"
            }
        }
        
        # Task-specific routing rules
        self.routing_rules = {
            TaskType.SUMMARIZE: {
                "priority": "speed",
                "preferred_models": [ModelType.GEMINI_FLASH, ModelType.GPT_4O_MINI],
                "min_quality": 6
            },
            TaskType.DRAFT: {
                "priority": "quality", 
                "preferred_models": [ModelType.GPT_4O_MINI, ModelType.CLAUDE_SONNET],
                "min_quality": 7
            },
            TaskType.TASKS: {
                "priority": "cost",
                "preferred_models": [ModelType.CLAUDE_HAIKU, ModelType.GPT_4O_MINI],
                "min_quality": 6
            },
            TaskType.CLASSIFY: {
                "priority": "speed",
                "preferred_models": [ModelType.GEMINI_FLASH, ModelType.GPT_4O_MINI],
                "min_quality": 5
            },
            TaskType.EXTRACT: {
                "priority": "balanced",
                "preferred_models": [ModelType.GPT_4O_MINI, ModelType.GEMINI_FLASH],
                "min_quality": 6
            },
            TaskType.ANALYZE: {
                "priority": "quality",
                "preferred_models": [ModelType.CLAUDE_SONNET, ModelType.GPT_4O],
                "min_quality": 8
            }
        }
        
        # Track usage for cost monitoring
        self.usage_stats = {
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_by_model": {},
            "session_start": time.time()
        }
    
    def choose_model(self, task: str, context_length: int = 1000, 
                    priority: str = None) -> str:
        """
        Choose optimal model for task
        
        Args:
            task: Task type (summarize, draft, tasks, etc.)
            context_length: Estimated token count 
            priority: Override priority (speed, cost, quality, balanced)
            
        Returns:
            Model name string
        """
        try:
            # Convert string to enum
            task_enum = TaskType(task.lower())
        except ValueError:
            # Default for unknown tasks
            task_enum = TaskType.DRAFT
        
        # Get routing config
        route_config = self.routing_rules.get(task_enum, self.routing_rules[TaskType.DRAFT])
        
        # Override priority if specified
        routing_priority = priority or route_config["priority"]
        
        # Filter models by requirements
        candidates = self._filter_candidates(
            route_config["preferred_models"],
            context_length,
            route_config["min_quality"]
        )
        
        if not candidates:
            # Fallback to GPT-4o-mini
            return ModelType.GPT_4O_MINI.value
        
        # Select based on priority
        selected = self._select_by_priority(candidates, routing_priority)
        
        # Track usage
        self._track_usage(selected, context_length)
        
        return selected.value
    
    def _filter_candidates(self, preferred_models: List[ModelType], 
                          context_length: int, min_quality: int) -> List[ModelType]:
        """Filter models by context limit and quality requirements"""
        candidates = []
        
        for model in preferred_models:
            config = self.model_configs[model]
            
            # Check context limit
            if context_length > config["context_limit"]:
                continue
                
            # Check quality requirement
            if config["quality_score"] < min_quality:
                continue
                
            candidates.append(model)
        
        return candidates
    
    def _select_by_priority(self, candidates: List[ModelType], priority: str) -> ModelType:
        """Select model based on priority criteria"""
        if priority == "speed":
            return max(candidates, key=lambda m: self.model_configs[m]["speed_score"])
        elif priority == "cost":
            return min(candidates, key=lambda m: self.model_configs[m]["cost_per_1k_tokens"])
        elif priority == "quality":
            return max(candidates, key=lambda m: self.model_configs[m]["quality_score"])
        else:  # balanced
            return self._select_balanced(candidates)
    
    def _select_balanced(self, candidates: List[ModelType]) -> ModelType:
        """Select model with best balanced score"""
        def balance_score(model: ModelType) -> float:
            config = self.model_configs[model]
            # Normalize scores (lower cost is better, higher speed/quality is better)
            cost_score = 1.0 / (config["cost_per_1k_tokens"] * 10000)  # Invert cost
            speed_score = config["speed_score"] / 10.0
            quality_score = config["quality_score"] / 10.0
            
            # Weighted average (adjust weights as needed)
            return (cost_score * 0.3 + speed_score * 0.4 + quality_score * 0.3)
        
        return max(candidates, key=balance_score)
    
    def _track_usage(self, model: ModelType, estimated_tokens: int):
        """Track model usage for cost monitoring"""
        model_name = model.value
        
        # Update stats
        self.usage_stats["total_tokens"] += estimated_tokens
        
        if model_name not in self.usage_stats["requests_by_model"]:
            self.usage_stats["requests_by_model"][model_name] = {
                "count": 0,
                "tokens": 0,
                "cost": 0.0
            }
        
        stats = self.usage_stats["requests_by_model"][model_name]
        stats["count"] += 1
        stats["tokens"] += estimated_tokens
        
        # Calculate cost
        cost_per_token = self.model_configs[model]["cost_per_1k_tokens"] / 1000
        request_cost = estimated_tokens * cost_per_token
        stats["cost"] += request_cost
        self.usage_stats["total_cost"] += request_cost
    
    def get_usage_report(self) -> Dict:
        """Get detailed usage and cost report"""
        session_duration = time.time() - self.usage_stats["session_start"]
        
        return {
            "session_duration_minutes": session_duration / 60,
            "total_requests": sum(
                stats["count"] for stats in self.usage_stats["requests_by_model"].values()
            ),
            "total_tokens": self.usage_stats["total_tokens"],
            "total_cost_usd": round(self.usage_stats["total_cost"], 4),
            "cost_per_request": round(
                self.usage_stats["total_cost"] / max(1, sum(
                    stats["count"] for stats in self.usage_stats["requests_by_model"].values()
                )), 4
            ),
            "models_used": self.usage_stats["requests_by_model"]
        }
    
    def recommend_model(self, task: str, requirements: Dict = None) -> Dict:
        """
        Get model recommendation with explanation
        
        Args:
            task: Task type
            requirements: Optional dict with context_length, priority, budget_limit
            
        Returns:
            Dict with recommended model and reasoning
        """
        requirements = requirements or {}
        
        context_length = requirements.get("context_length", 1000)
        priority = requirements.get("priority")
        budget_limit = requirements.get("budget_limit")  # USD per request
        
        # Get standard recommendation
        recommended_model = self.choose_model(task, context_length, priority)
        model_enum = ModelType(recommended_model)
        config = self.model_configs[model_enum]
        
        # Calculate estimated cost
        estimated_cost = (context_length / 1000) * config["cost_per_1k_tokens"]
        
        # Check budget constraint
        within_budget = budget_limit is None or estimated_cost <= budget_limit
        
        # Generate alternatives if needed
        alternatives = []
        if not within_budget:
            # Find cheaper alternatives
            for model_type in ModelType:
                model_config = self.model_configs[model_type]
                alt_cost = (context_length / 1000) * model_config["cost_per_1k_tokens"]
                if alt_cost <= budget_limit:
                    alternatives.append({
                        "model": model_type.value,
                        "cost": alt_cost,
                        "quality_score": model_config["quality_score"],
                        "speed_score": model_config["speed_score"]
                    })
        
        return {
            "recommended_model": recommended_model,
            "estimated_cost": round(estimated_cost, 6),
            "within_budget": within_budget,
            "reasoning": self._generate_reasoning(task, model_enum, requirements),
            "alternatives": sorted(alternatives, key=lambda x: x["quality_score"], reverse=True)[:3],
            "model_config": config
        }
    
    def _generate_reasoning(self, task: str, model: ModelType, requirements: Dict) -> str:
        """Generate human-readable reasoning for model choice"""
        config = self.model_configs[model]
        task_config = self.routing_rules.get(TaskType(task.lower()), {})
        
        reasoning_parts = []
        
        # Task-specific reasoning
        if task == "summarize":
            reasoning_parts.append(f"For summarization, prioritizing speed and cost-effectiveness.")
        elif task == "draft":
            reasoning_parts.append(f"For drafting, prioritizing response quality and coherence.")
        elif task == "tasks":
            reasoning_parts.append(f"For task extraction, prioritizing cost while maintaining accuracy.")
        
        # Model-specific reasoning
        reasoning_parts.append(f"{model.value} offers quality score {config['quality_score']}/10, "
                             f"speed score {config['speed_score']}/10, "
                             f"at ${config['cost_per_1k_tokens']:.6f} per 1K tokens.")
        
        # Context reasoning
        context_length = requirements.get("context_length", 1000)
        if context_length > 50000:
            reasoning_parts.append(f"Large context ({context_length} tokens) requires high-capacity model.")
        
        return " ".join(reasoning_parts)

    def get_cost_optimization_tips(self) -> List[str]:
        """Get tips for optimizing costs"""
        tips = []
        
        usage = self.get_usage_report()
        
        if usage["total_cost_usd"] > 1.0:
            tips.append("Consider using Gemini Flash for summarization tasks to reduce costs by ~50%")
        
        if usage["total_tokens"] > 100000:
            tips.append("For high-volume processing, consider caching summaries and responses")
        
        expensive_models = [model for model, stats in usage["models_used"].items() 
                           if stats["cost"] > 0.10]
        if expensive_models:
            tips.append(f"Monitor usage of expensive models: {', '.join(expensive_models)}")
        
        if not tips:
            tips.append("Current usage is cost-efficient. Consider quality upgrades if needed.")
        
        return tips