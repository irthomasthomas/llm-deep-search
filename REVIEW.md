INFO:llm_websearch.config:Settings loaded successfully. Log Level: INFO
INFO:llm_websearch.config:LLM Default: gemini-2.0-flash-exp, Cache: True
INFO:llm_websearch.config:Cache directory ensured: /home/thomas/.cache/llm_websearch
INFO:llm_websearch.utils:Disk cache initialized: /home/thomas/.cache/llm_websearch (TTL: 86400s)
INFO:llm_websearch:'websearch' command group registered.
INFO:llm_websearch.cli:Executing deep-search: 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.' (Num Results/Iter=5, Timeout=30.0, Max Iter=1, Format=full)
INFO:llm_websearch.core:Core Deep Search (Refactored): 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.', num=5, iter=1, fmt=full
INFO:llm_websearch.components.llm_integration:Google GenAI client configured successfully.
INFO:llm_websearch.components.query_expansion:QueryExpander init: max_v=5, min_conf=0.7
INFO:llm_websearch.utils:Creating aiolimiter 'llm_api' rate 5.0/1.0s
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'sem_q_exp'
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'sem_q_exp' (3.20s). Tokens: 574
INFO:llm_websearch.components.query_expansion:Q_exp for 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.' done in 3.20s. Gen 5 variants.
INFO:llm_websearch.core:Expanded 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.' to 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.' (confidence: 1.00)
INFO:llm_websearch.core:Initializing DeepResearcher...
INFO:llm_websearch.components.deep_research:DeepResearcher initialized: max_iter=1, max_branch=3, rel_thresh=0.6, dim_ret=0.1
INFO:llm_websearch.core:Starting DeepResearcher for query: 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.'...
INFO:llm_websearch.components.deep_research:Starting async deep research for: 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.'
INFO:llm_websearch.components.deep_research:Exploring Path d103d40e-52f0-4c78-b949-ccdb91a11433 (Depth 1/1): anthropic 2025 prompt caching api changes - and code example using latest newest api changes.
INFO:llm_websearch.core:search_fn_closure called for query: 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.'
INFO:llm_websearch.core:Core Search (Refactored): 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.', num=5, timeout=30.0, filter=True
INFO:llm_websearch.utils:Creating aiolimiter 'google_search' rate 8.0/1.0s
INFO:llm_websearch.utils:Creating aiolimiter 'bing_search' rate 2.0/1.0s
INFO:httpx:HTTP Request: GET https://www.googleapis.com/customsearch/v1?key=AIzaSyACQp3L8cNuRrncv6MmcQpR6TYRMHVhWsA&cx=03d63c3b7533f4a86&q=anthropic+2025+prompt+caching+api+changes+-+and+code+example+using+latest+newest+api+changes.&num=3&start=1&safe=active "HTTP/1.1 200 OK"
INFO:llm_websearch.search_engines.google:Google Search returned 3 results for 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.'
INFO:httpx:HTTP Request: GET https://api.bing.microsoft.com/v7.0/custom/search?q=anthropic+2025+prompt+caching+api+changes+-+and+code+example+using+latest+newest+api+changes.&customConfig=6a23d0dc-6abc-412e-a72f-1333d02e0027&count=2&offset=0&responseFilter=Webpages&safeSearch=Strict "HTTP/1.1 200 OK"
INFO:llm_websearch.search_engines.bing:Bing Search returned 2 results for 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.'
INFO:llm_websearch.core:Deduplicated 5 results to 4.
INFO:llm_websearch.core:Applying fast filter...
INFO:llm_websearch.components.llm_integration:Google GenAI client configured successfully.
INFO:llm_websearch.components.fast_filter:Starting async fast filter batch for 4 items.
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_scoring'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_scoring'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_scoring'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_scoring'
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_scoring' (0.50s). Tokens: 189
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_scoring' (0.77s). Tokens: 172
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_scoring' (0.81s). Tokens: 173
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_scoring' (0.92s). Tokens: 170
INFO:llm_websearch.components.fast_filter:Async fast filter batch completed. Processed 4/4. 3 items passed threshold.
INFO:llm_websearch.core:Fast filter kept 3/4 items.
INFO:llm_websearch.core:Sorted and sliced results, returning 3.
INFO:llm_websearch.components.detailed_analysis:Starting analysis of 3 search results for query: 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.'
INFO:llm_websearch.components.detailed_analysis:Starting async batch analysis for 3 content chunks.
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_analysis'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_analysis'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_analysis'
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_analysis' (0.47s). Tokens: 114
INFO:llm_websearch.components.detailed_analysis:Calculated relevance via LLM: 0.50
INFO:llm_websearch.components.detailed_analysis:Detailed analysis completed in 0.47s.
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_analysis' (0.50s). Tokens: 132
INFO:llm_websearch.components.detailed_analysis:Calculated relevance via LLM: 0.90
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_points_extraction'
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_analysis' (0.64s). Tokens: 108
INFO:llm_websearch.components.detailed_analysis:Calculated relevance via LLM: 0.80
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_points_extraction'
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'key_points_extraction' (0.86s). Tokens: 185
INFO:llm_websearch.components.detailed_analysis:Extracted 4 key points via LLM.
INFO:llm_websearch.components.detailed_analysis:Detailed analysis completed in 1.36s.
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'key_points_extraction' (0.78s). Tokens: 148
INFO:llm_websearch.components.detailed_analysis:Extracted 3 key points via LLM.
INFO:llm_websearch.components.detailed_analysis:Detailed analysis completed in 1.42s.
INFO:llm_websearch.components.detailed_analysis:Async batch analysis finished in 1.42s. Processed ~3/3. Relevant: 2.
INFO:llm_websearch.components.detailed_analysis:Completed analysis, 2 results met threshold.
WARNING:llm_websearch.core:search_fn_closure: No analysis found for snippet: Aug 14, 2024 ... ... changes, where each step typi...
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'relevance_analysis'
INFO:llm_websearch.components.llm_integration:LLM 'gemini-2.0-flash-exp' successful for task 'relevance_analysis' (0.40s). Tokens: 213
INFO:llm_websearch.components.detailed_analysis:Calculated relevance via LLM: 0.95
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_points_extraction'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 13
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_points_extraction'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 10
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_points_extraction'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 7
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.detailed_analysis:LLM error during key points extraction: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 7
}
]
WARNING:llm_websearch.components.detailed_analysis:Falling back to simple key points extraction.
INFO:llm_websearch.components.detailed_analysis:Extracted 3 key points via fallback.
INFO:llm_websearch.components.detailed_analysis:Detailed analysis completed in 6.55s.
INFO:llm_websearch.components.deep_research:Added 3 insights via Analyzer.
INFO:llm_websearch.components.deep_research:Exploration complete. Synthesizing findings and contradictions...
INFO:llm_websearch.components.deep_research:Synthesizing key findings from 3 collected insights...
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'finding_synth'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 7
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'finding_synth'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 4
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'finding_synth'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 1
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
WARNING:llm_websearch.components.deep_research:LLM finding synthesis failed: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 1
}
]. Fallback.
INFO:llm_websearch.components.deep_research:Added 3 findings via fallback insight selection.
INFO:llm_websearch.components.deep_research:Need >= 2 paths for contradictions.
INFO:llm_websearch.components.deep_research:Deep research 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.' status 'Completed' in 15.74s. Paths: 1. Depth: 0
INFO:llm_websearch.core:DeepResearcher completed with status: Completed
INFO:llm_websearch.core:Starting summarization of research result...
INFO:llm_websearch.components.summarization:Starting async summarization of ResearchResult.
INFO:llm_websearch.components.summarization:Total text items for summarization: 3
INFO:llm_websearch.components.summarization:Calling async internal summarize method.
INFO:llm_websearch.components.summarization:Starting async summarization for 3 content items.
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 57
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 56
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 3: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 3, using mock.
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 1: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 1, using mock.
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 1: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 1, using mock.
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 2: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 2, using mock.
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 2: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 2, using mock.
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 3: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 3, using mock.
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L1'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 1: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 1, using mock.
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L2'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 2: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 54
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 2, using mock.
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summarization_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 53
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating summary level 3: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 53
}
]
WARNING:llm_websearch.components.summarization:LLM unavailable/failed for summary level 3, using mock.
INFO:llm_websearch.components.summarization:Generating combined summaries.
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L1'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L2'
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 53
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 53
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 53
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L1'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 50
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L2'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 50
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 50
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L1'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 47
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating combined summary level 1: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 47
}
]
WARNING:llm_websearch.components.summarization:LLM failed/unavailable for combined summary level 1, using fallback.
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L2'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 47
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating combined summary level 2: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 47
}
]
WARNING:llm_websearch.components.summarization:LLM failed/unavailable for combined summary level 2, using fallback.
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'summary_synthesis_L3'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 47
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error generating combined summary level 3: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 47
}
]
WARNING:llm_websearch.components.summarization:LLM failed/unavailable for combined summary level 3, using fallback.
INFO:llm_websearch.components.summarization:Extracting key insights.
INFO:llm_websearch.components.llm_integration:Attempt 1/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_insights'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 1 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 47
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 2/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_insights'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 2 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 43
}
]
INFO:llm_websearch.components.llm_integration:Retrying in 3s...
INFO:llm_websearch.components.llm_integration:Attempt 3/3: Calling LLM 'gemini-2.0-flash-exp' for task 'key_insights'
WARNING:llm_websearch.components.llm_integration:LLM API attempt 3 failed for model 'gemini-2.0-flash-exp': ResourceExhausted: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 40
}
]
ERROR:llm_websearch.components.llm_integration:LLM API call failed after 3 attempts for model 'gemini-2.0-flash-exp'.
ERROR:llm_websearch.components.summarization:LLM error extracting key insights: API call failed after retries: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. [violations {
}
, links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, retry_delay {
  seconds: 40
}
]
WARNING:llm_websearch.components.summarization:LLM integration not available or failed, using mock key insights.
INFO:llm_websearch.components.summarization:Extracted 3 key insights.
INFO:llm_websearch.components.summarization:Async summarization completed in 20.07 seconds.
INFO:llm_websearch.components.summarization:Internal summarize method completed.
INFO:llm_websearch.components.summarization:Successfully generated summary data for ResearchResult.
INFO:llm_websearch.core:Summarization complete.
INFO:llm_websearch.core:Formatting research result (Status: Completed, Format: full).
INFO:llm_websearch.core:Deep search for 'anthropic 2025 prompt caching api changes - and code example using latest newest api changes.' finished successfully.
# Deep Search Results for: "anthropic 2025 prompt caching api changes - and code example using latest newest api changes."
**Status:** Completed

## Key Findings
1. **Finding:** Prompt caching is a powerful feature that optimizes your API usage by allowing resuming from specific prefixes in your prompts 
   - **Confidence:** 0.68
   - **Source:** fallback_insight_selection
   - **Relevant Path IDs:** d103d40e-52f0-4c78-b949-ccdb91a11433
2. **Finding:** This approach significantly reduces processing time and costs for repetitive tasks or prompts with consistent elements 
   - **Confidence:** 0.68
   - **Source:** fallback_insight_selection
   - **Relevant Path IDs:** d103d40e-52f0-4c78-b949-ccdb91a11433
3. **Finding:** Here’s an example of how to implement prompt caching with the Messages API using a cache_control ...

Aug 14, 2024 .. 
   - **Confidence:** 0.68
   - **Source:** fallback_insight_selection
   - **Relevant Path IDs:** d103d40e-52f0-4c78-b949-ccdb91a11433

## Summaries
### Short Summary
Mock short summary. Mock short summary. Mock short summary.

### Medium Summary
Mock medium summary. Mock medium summary. Mock medium summary.

### Detailed Summary
Mock detailed summary. Mock detailed summary. Mock detailed summary.


## Overall Key Insights
- Mock Key Insight 1
- Mock Key Insight 2
- Mock Key Insight 3

## Exploration Paths
### Path: d103d40e-52f0-4c78-b949-ccdb91a11433 (Depth: 0)
- **Query:** "anthropic 2025 prompt caching api changes - and code example using latest newest api changes."
- **Parent:** Root
- **Explored:** True
- **Relevance:** 0.00
- **Insights:**
  - Prompt caching is a powerful feature that optimizes your API usage by allowing resuming from specific prefixes in your prompts (Conf: 0.76, Src: analyzer)
  - This approach significantly reduces processing time and costs for repetitive tasks or prompts with consistent elements (Conf: 0.76, Src: analyzer)
  - Here’s an example of how to implement prompt caching with the Messages API using a cache_control ...

Aug 14, 2024 .. (Conf: 0.76, Src: analyzer)
- **Search Results (3):**
  - [Prompt caching - Anthropic](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) (Rank: 1)
    > Prompt caching is a powerful feature that optimizes your API usage by allowing resuming from specific prefixes in your prompts. This approach signific...
  - [Prompt caching with Claude \ Anthropic](https://www.anthropic.com/news/prompt-caching) (Rank: 1)
    > Aug 14, 2024 ... ... changes, where each step typically requires a new API call. Talk to books, papers, documentation, podcast transcripts, and other ...
  - [Token-saving updates on the Anthropic API \ Anthropic](https://www.anthropic.com/news/token-saving-updates) (Rank: 3)
    > Mar 13, 2025 ... ... with minimal code changes. Increase your ... A comparison of prompt caching with and without automatic use of the largest cached ...

## Exploration Metrics
- Paths Explored: 1
- Max Depth Reached: 0
- Total Results Collected: 3
- Total Duration: 15.74 seconds

## Draft Proposal
To improve the `llm-websearch` tool's handling of rate limits with the Google Gemini API, modify the `LLMIntegration.generate_response` method in `llm_websearch/components/llm_integration.py` to implement model fallback.

1.  **Modify Imports:**
    *   In `llm_websearch/components/llm_integration.py`, import `ResourceExhausted` from `google.generativeai.errors`.
    *   Define a dummy `ResourceExhausted` class within the `except ImportError` block for `google.generativeai` to prevent errors if the library is missing.

2.  **Update API Key Configuration:**
    *   In `LLMIntegration.__init__`, prioritize `settings.llm_api_key` over `settings.google_api_key` when configuring `genai`.
    *   Update the related error/warning messages if no key is found.

3.  **Implement Model Sequence Generation:**
    *   Create a new private method `_get_model_sequence(self, requested_model: Optional[str] = None) -> List[str]`.
    *   This method will construct an ordered list of unique Gemini model names to try, based on:
        1.  `requested_model` (if provided and valid)
        2.  `settings.llm_model_default`
        3.  Models listed in `settings.llm_primary_models`
        4.  Models listed in `settings.llm_fallback_models`
    *   Ensure the method only adds valid Gemini model names (starting with 'gemini') and avoids duplicates.
    *   Log the generated sequence.

4.  **Refactor `generate_response` Method:**
    *   Call `_get_model_sequence` at the beginning to get the list of models to try. Handle the case where the sequence is empty.
    *   Introduce an outer `for current_model_name in model_sequence:` loop.
    *   Move the cache check *inside* this outer loop, ensuring the cache key generation (`_create_cache_key`) uses `current_model_name`.
    *   The existing retry logic (`for attempt in range(max_retries + 1):`) becomes the inner loop.
    *   Update logging within the loops to indicate the current model and attempt number.
    *   Modify the `GenerationConfig` setup to potentially set `response_mime_type` based on `current_model_name` and `response_format`.

5.  **Implement Rate Limit Handling (429):**
    *   Inside the inner retry loop's `try...except` block, add a specific `except ResourceExhausted as e:` clause before the generic `except Exception`.
    *   In this `ResourceExhausted` block:
        *   Log a warning indicating a rate limit was hit for the `current_model_name`.
        *   Use `break` to exit the *inner* retry loop immediately, allowing the outer loop to proceed to the next model.

6.  **Adjust General Exception Handling:**
    *   The generic `except Exception as e:` in the inner loop should continue to handle other errors. If retries are exhausted for *this* model due to non-429 errors, it should also `break` the inner loop.
    *   After the outer loop finishes (meaning all models in the sequence were tried and failed), check if a successful response was returned. If not, raise a final `LLMError` summarizing that all models failed, including the `last_exc`.

7.  **Update `LLMResponse` Instantiation:**
    *   Add the `system_prompt_used=system_prompt` argument when creating the `LLMResponse` object upon success.

8.  **Testing and Validation (Conceptual):**
    *   Define conceptual test cases to verify the fallback logic:
        *   Simulate `ResourceExhausted` for the default model and check if a fallback model is used.
        *   Simulate persistent non-429 errors for a model and check if retries happen before fallback.
        *   Simulate errors for *all* models and check if the final `LLMError` is raised correctly.
        *   Verify caching uses the correct model name in the key.

Notes:
Test the plugin using:
.venv/bin/llm install /home/thomas/Projects/llm/plugins/Utilities/llm-search/llm-deep-search-v4

If there is an error use:
LLM_LOAD_PLUGINS='' .venv/bin/llm uninstall llm-websearch -y

If you want to see how I use bing search api already, check /home/thomas/Projects/claude.sh/utils/search/bing-search.sh

And if you need to see google search api check /home/thomas/Projects/claude.sh/utils/search/google-search-llm.sh

Test your work regularly using smoke tests, unit tests or integration tests.
Test the plugin using:  .venv/bin/llm websearch deep-search "anthropic 2025 api prompt caching"
or similar.

