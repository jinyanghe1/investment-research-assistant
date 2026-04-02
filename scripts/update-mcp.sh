#!/bin/bash
# =============================================================================
# update-mcp.sh - 动态更新投研助手 MCP 配置
#
# 用途：
#   1. 自动扫描 mcp/tools/ 下的所有工具模块
#   2. 更新 .mcp.json 配置
#   3. 更新 mcp/server.py 中的模块注册列表
#   4. 生成工具清单文档
#
# 使用：
#   ./scripts/update-mcp.sh           # 完整更新
#   ./scripts/update-mcp.sh --check    # 仅检查工具列表
#   ./scripts/update-mcp.sh --verify  # 验证 MCP Server 可启动
# =============================================================================

set -e

PROJECT_ROOT="/Users/hejinyang/投研助手"
MCP_DIR="$PROJECT_ROOT/mcp"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# -----------------------------------------------------------------------------
# 函数：扫描工具模块
# -----------------------------------------------------------------------------
scan_tools() {
    local tools_dir="$MCP_DIR/tools"
    local modules=()

    if [[ ! -d "$tools_dir" ]]; then
        log_error "工具目录不存在: $tools_dir"
        return 1
    fi

    for py_file in "$tools_dir"/*.py; do
        if [[ -f "$py_file" ]]; then
            local basename=$(basename "$py_file" .py)
            # 跳过 __init__ 和其他非工具文件
            if [[ "$basename" != "__init__" ]]; then
                modules+=("$basename")
            fi
        fi
    done

    echo "${modules[@]}"
}

# -----------------------------------------------------------------------------
# 函数：更新 .mcp.json
# -----------------------------------------------------------------------------
update_mcp_json() {
    local tools="$1"
    local timestamp=$(date '+%Y-%m-%d')

    log_info "更新 .mcp.json..."

    # 将工具列表转为 JSON 数组
    local tools_json=$(echo "$tools" | tr ' ' '\n' | jq -R . | jq -s .)
    [[ "$tools_json" == "null" ]] && tools_json="[]"

    cat > "$PROJECT_ROOT/.mcp.json" << EOF
{
  "mcpServers": {
    "投研助手": {
      "command": "python3",
      "args": [
        "-m",
        "mcp.server"
      ],
      "cwd": "$PROJECT_ROOT",
      "env": {
        "PYTHONPATH": "$PROJECT_ROOT"
      }
    }
  },
  "metadata": {
    "name": "投研助手 MCP",
    "version": "1.0.0",
    "description": "AI驱动的全链路投研工具集",
    "projectPath": "$PROJECT_ROOT",
    "lastUpdated": "$timestamp",
    "tools": $tools_json
  }
}
EOF

    log_info ".mcp.json 已更新"
}

# -----------------------------------------------------------------------------
# 函数：更新 server.py 中的模块注册
# -----------------------------------------------------------------------------
update_server_py() {
    local tools="$1"

    log_info "更新 mcp/server.py..."

    # 构建模块列表字符串
    local modules_str=""
    for tool in $tools; do
        modules_str="\"$tool\", $modules_str"
    done
    modules_str=${modules_str%, }  # 移除末尾逗号

    # 使用 sed 更新 MODULE_NAME 列表
    # 注意：这是简单替换，实际可能需要更复杂的逻辑
    sed -i.bak "s/tool_modules = \[.*\]/tool_modules = [$modules_str]/" "$MCP_DIR/server.py"

    # 验证更新
    if grep -q "tool_modules = \[$modules_str\]" "$MCP_DIR/server.py"; then
        log_info "server.py 已更新"
    else
        log_warn "server.py 更新可能失败，请手动检查"
    fi

    # 移除备份
    rm -f "$MCP_DIR/server.py.bak"
}

# -----------------------------------------------------------------------------
# 函数：生成工具清单
# -----------------------------------------------------------------------------
generate_tools_list() {
    local tools="$1"
    local output_file="$PROJECT_ROOT/MCP_TOOLS.md"

    log_info "生成工具清单..."

    cat > "$output_file" << EOF
# MCP 工具清单

> 自动生成 - $(date '+%Y-%m-%d %H:%M:%S')

## 工具模块

| 序号 | 模块名称 | 状态 | 说明 |
|------|----------|------|------|
EOF

    local index=1
    for tool in $tools; do
        local status="✅ 可用"
        local desc=""

        # 根据模块名添加描述
        case "$tool" in
            market_data) desc="行情数据：股票、指数、期货" ;;
            macro_data) desc="宏观分析：GDP、CPI、PMI、政策" ;;
            company_analysis) desc="公司研究：财务、估值、产业链" ;;
            fundamental_analysis) desc="基本面分析：杜邦分析、DCF估值" ;;
            technical_analysis) desc="技术分析：K线形态、技术指标" ;;
            futures_data) desc="期货数据：国内外期货品种" ;;
            report_generator) desc="研报生成：HTML研报自动生成" ;;
            knowledge_base) desc="知识库：研报索引与检索" ;;
            *) desc="其他工具" ;;
        esac

        echo "| $index | \`$tool\` | $status | $desc |" >> "$output_file"
        index=$((index + 1))
    done

    echo "" >> "$output_file"
    echo "## 安装状态" >> "$output_file"
    echo "" >> "$output_file"
    echo "```bash" >> "$output_file"
    echo "cd $MCP_DIR" >> "$output_file"
    echo "pip install -r requirements.txt" >> "$output_file"
    echo "python3 -m mcp.server --test" >> "$output_file"
    echo "```" >> "$output_file"

    log_info "工具清单已生成: $output_file"
}

# -----------------------------------------------------------------------------
# 函数：验证 MCP Server
# -----------------------------------------------------------------------------
verify_server() {
    log_info "验证 MCP Server..."

    # 检查 Python 环境
    if ! command -v python3 &> /dev/null; then
        log_error "python3 未安装"
        return 1
    fi

    # 检查依赖
    if ! python3 -c "import fastmcp" 2>/dev/null; then
        log_warn "FastMCP 未安装，正在安装..."
        pip install fastmcp
    fi

    # 尝试导入 server
    if python3 -c "import sys; sys.path.insert(0, '$MCP_DIR'); from server import mcp" 2>/dev/null; then
        log_info "✅ MCP Server 导入成功"
        return 0
    else
        log_error "❌ MCP Server 导入失败"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# 函数：显示帮助
# -----------------------------------------------------------------------------
show_help() {
    cat << EOF
用法: $(basename "$0") [选项]

动态更新投研助手 MCP 配置

选项:
  --check     仅扫描并显示工具列表
  --verify    验证 MCP Server 可启动
  --help      显示此帮助信息

示例:
  $(basename "$0")           # 完整更新
  $(basename "$0") --check    # 检查工具
  $(basename "$0") --verify  # 验证安装

EOF
}

# =============================================================================
# 主逻辑
# =============================================================================

main() {
    cd "$PROJECT_ROOT"

    case "${1:-}" in
        --check)
            log_info "扫描工具模块..."
            tools=$(scan_tools)
            echo ""
            echo "发现工具模块:"
            for tool in $tools; do
                echo "  - $tool"
            done
            echo ""
            echo "共 ${#tools[@]} 个模块"
            ;;
        --verify)
            verify_server
            ;;
        --help)
            show_help
            ;;
        "")
            log_info "=== 投研助手 MCP 动态更新 ==="
            echo ""

            # 1. 扫描工具
            log_info "步骤1: 扫描工具模块..."
            tools=$(scan_tools)
            echo "发现工具: $tools"
            echo ""

            # 2. 更新配置
            log_info "步骤2: 更新配置文件..."
            update_mcp_json "$tools"
            update_server_py "$tools"
            echo ""

            # 3. 生成文档
            log_info "步骤3: 生成文档..."
            generate_tools_list "$tools"
            echo ""

            # 4. 验证
            log_info "步骤4: 验证安装..."
            verify_server

            echo ""
            log_info "=== 更新完成 ==="
            echo ""
            echo "下一步:"
            echo "  1. 重启 Claude Code 以加载新配置"
            echo "  2. 或运行: claude -p \"列出MCP工具\" 验证"
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
