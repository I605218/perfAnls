-- =====================================================
-- Process Engine Performance Analysis SQL Queries
-- =====================================================
-- 本文件包含项目中使用的所有 SQL 查询，用于文档参考和测试

-- =====================================================
-- 1. Top K 最慢流程查询
-- =====================================================
-- 功能：查询执行时间最长的流程实例
-- 参数：
--   $1 - start_time (timestamp)
--   $2 - end_time (timestamp)
--   $3 - k (integer)

SELECT
    e.id,
    e.proc_def_id,
    d.name_ as proc_def_name,
    d.key_ as proc_def_key,
    e.proc_inst_name,
    e.start_time,
    e.end_time,
    EXTRACT(EPOCH FROM (e.end_time - e.start_time)) as duration_seconds,
    e.status,
    e.sub_status,
    e.error_message,
    e.tenant_id
FROM pe_ext_procinst e
LEFT JOIN act_re_procdef d ON e.proc_def_id = d.id_
WHERE e.end_time IS NOT NULL
  AND e.start_time >= $1
  AND e.end_time <= $2
ORDER BY duration_seconds DESC
LIMIT $3;

-- =====================================================
-- 2. 最频繁运行流程查询
-- =====================================================
-- 功能：统计运行次数最多的流程定义
-- 参数：
--   $1 - start_time (timestamp)
--   $2 - end_time (timestamp)
--   $3 - limit (integer)

SELECT
    d.key_ as proc_def_key,
    d.name_ as proc_def_name,
    d.version_,
    COUNT(*) as execution_count,
    COALESCE(
        ROUND(AVG(EXTRACT(EPOCH FROM (e.end_time - e.start_time)))::numeric, 2),
        0
    ) as avg_duration_seconds,
    COALESCE(
        ROUND(MIN(EXTRACT(EPOCH FROM (e.end_time - e.start_time)))::numeric, 2),
        0
    ) as min_duration,
    COALESCE(
        ROUND(MAX(EXTRACT(EPOCH FROM (e.end_time - e.start_time)))::numeric, 2),
        0
    ) as max_duration
FROM pe_ext_procinst e
JOIN act_re_procdef d ON e.proc_def_id = d.id_
WHERE e.start_time >= $1
  AND e.start_time <= $2
GROUP BY d.key_, d.name_, d.version_
ORDER BY execution_count DESC
LIMIT $3;

-- =====================================================
-- 3. 活动级别性能分析
-- =====================================================
-- 功能：分析指定流程实例中各活动的执行性能
-- 参数：
--   $1 - proc_inst_id (varchar)

SELECT
    a.act_id,
    a.act_name,
    a.act_type,
    COUNT(*) as execution_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (a.end_time - a.start_time)))::numeric, 2)
        as avg_duration,
    ROUND(MAX(EXTRACT(EPOCH FROM (a.end_time - a.start_time)))::numeric, 2)
        as max_duration,
    ROUND(MIN(EXTRACT(EPOCH FROM (a.end_time - a.start_time)))::numeric, 2)
        as min_duration
FROM pe_ext_actinst a
WHERE a.proc_inst_id = $1
  AND a.end_time IS NOT NULL
GROUP BY a.act_id, a.act_name, a.act_type
ORDER BY avg_duration DESC;

-- =====================================================
-- 4. 数据库基础统计查询
-- =====================================================

-- 流程实例总数
SELECT COUNT(*) as total_instances
FROM pe_ext_procinst;

-- 已完成的流程实例
SELECT COUNT(*) as completed_instances
FROM pe_ext_procinst
WHERE end_time IS NOT NULL;

-- 流程定义数量
SELECT COUNT(*) as process_definitions
FROM act_re_procdef;

-- 部署数量
SELECT COUNT(*) as deployments
FROM act_re_deployment;

-- 最近一次流程实例时间
SELECT MAX(start_time) as latest_instance
FROM pe_ext_procinst;

-- =====================================================
-- 5. 核心表检查查询
-- =====================================================

-- 检查所有表
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 检查核心表是否存在
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('pe_ext_procinst', 'pe_ext_actinst', 'pe_ext_varinst', 'act_re_procdef')
ORDER BY table_name;

-- =====================================================
-- 6. 测试数据验证查询
-- =====================================================

-- 查看最近的流程实例
SELECT
    id,
    proc_inst_name,
    start_time,
    end_time,
    EXTRACT(EPOCH FROM (e.end_time - e.start_time)) as duration_seconds,
    status
FROM pe_ext_procinst e
WHERE end_time IS NOT NULL
ORDER BY start_time DESC
LIMIT 10;

-- 查看流程定义列表
SELECT
    key_,
    name_,
    version_,
    deployment_id_,
    create_time_
FROM act_re_procdef
ORDER BY create_time_ DESC
LIMIT 10;

-- =====================================================
-- 7. 性能优化相关查询
-- =====================================================

-- 查找长时间运行的流程（超过5分钟）
SELECT
    e.id,
    d.name_ as proc_def_name,
    EXTRACT(EPOCH FROM (e.end_time - e.start_time)) as duration_seconds,
    e.start_time,
    e.end_time
FROM pe_ext_procinst e
JOIN act_re_procdef d ON e.proc_def_id = d.id_
WHERE e.end_time IS NOT NULL
  AND EXTRACT(EPOCH FROM (e.end_time - e.start_time)) > 300
ORDER BY duration_seconds DESC;

-- 查找失败的流程实例
SELECT
    e.id,
    d.name_ as proc_def_name,
    e.status,
    e.error_message,
    e.start_time
FROM pe_ext_procinst e
JOIN act_re_procdef d ON e.proc_def_id = d.id_
WHERE e.status LIKE '%FAIL%' OR e.status LIKE '%ERROR%'
ORDER BY e.start_time DESC;

-- =====================================================
-- 说明
-- =====================================================
-- 这些 SQL 查询在代码中通过参数化方式执行，防止 SQL 注入
-- 所有时间计算使用 EXTRACT(EPOCH FROM ...) 转换为秒数
-- LEFT JOIN 用于处理流程定义可能被删除的情况
-- COALESCE 用于处理 NULL 值，确保始终返回数值
