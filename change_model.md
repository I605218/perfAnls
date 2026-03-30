根据前面的修改记录，需要修改模型配置的位置如下：
                                                                                                                                                                                                                                                          
需要修改的文件和位置：                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                          
1. 环境变量文件                                                                                                                                                                                                                                           

- 文件: .env（项目根目录）                                                                                                                                                                                                                                
- 位置: 第9行                                                                                                                                                                                                                                             
- 修改: CLAUDE_MODEL=claude-haiku-4-5                                                                                                                                                                                                                     
                                                                                                                                                                                                                                                          
2. 配置文件                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                                          
- 文件: app/config.py                                                                                                                                                                                                                                     
- 位置: 第27行                                                                                                                                                                                                                                            
- 修改: claude_model: str = "claude-haiku-4-5"                                                                                                                                                                                                            
                                                                                                                                                                                                                                                          
3. Text-to-SQL服务                                                                                                                                                                                                                                        

- 文件: app/services/text_to_sql_service.py
- 位置: 第85行（__init__ 方法的默认参数）
- 修改: model: str = "claude-haiku-4-5",

4. AI分析服务

- 文件: app/services/ai_analysis_service.py
- 位置: 第62行（__init__ 方法的默认参数）
- 修改: model: str = "claude-haiku-4-5",

5. API响应模型示例

- 文件: app/api/models/responses.py
- 位置: 第64行和第99行（两处示例）
- 修改: "model": "claude-haiku-4-5",

可用的模型选项：

- claude-haiku-4-5 - 最快，成本最低（当前使用）
- claude-sonnet-4-6 - 平衡速度和准确度
- claude-opus-4-6 - 最准确，最慢，成本最高

修改后记得：

1. 重启服务才能生效
2. 如果只改 .env，运行中的服务不会自动重新加载
3. 如果要改回 Sonnet，把所有 haiku-4-5 替换成 sonnet-4-6 即可