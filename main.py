import requests
import json
from rich import print as rprint
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.console import Console
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

console = Console()

def custom_header(title, subtitle=None):
    header_text = Text(title, style="bold cyan")
    if subtitle:
        header_text.append(f"\n{subtitle}", style="dim")
    return Panel(Align.center(header_text), border_style="blue", title="Ollama API T00l")

def print_info(message):
    rprint(Panel(f"[bold green]{message}[/bold green]", title="INFO"))

def print_error(message):
    rprint(Panel(f"[bold red]{message}[/bold red]", title="ERROR"))

def safe_print(message):
    return str(message).strip() if message else "NONE"

def call_ollama_api(url, endpoint, method="GET", json_data=None):
    api_endpoint = f"{url}/api/{endpoint}"
    try:
        if method == "POST":
            response = requests.post(api_endpoint, json=json_data, verify=False)
        elif method == "DELETE":
            response = requests.delete(api_endpoint, json=json_data, verify=False)
        else:
            response = requests.get(api_endpoint, verify=False)

        if response.status_code in [200, 204]:
            if response.status_code == 204:
                return True
            try:
                return response.json()
            except ValueError:
                return response.text
        else:
            print_error(f"请求失败，状态码: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print_error(f"网络请求失败: {e}")
        return None

def list_models(url):
    result = call_ollama_api(url, "tags")
    if result and "models" in result:
        models = result["models"]
        if not models:
            print_info("没有找到任何模型。")
            return

        model_list = ""
        for idx, model in enumerate(models, start=1):
            model_name = model.get("name", "未知名称")
            model_size = human_readable_size(model.get("size", 0))
            modified_at = model.get("modified_at", "未知修改时间")
            digest = model.get("digest", "未知摘要")

            details = model.get("details", {})
            family = details.get("family", "未知家族")
            parameter_size = details.get("parameter_size", "未知参数量")
            quantization_level = details.get("quantization_level", "未知量化级别")
            format_type = details.get("format", "未知格式")

            model_list += f"[bold cyan]{idx}. {model_name}[/bold cyan]\n"
            model_list += f"  - 大小: {model_size}\n"
            model_list += f"  - 修改时间: {modified_at}\n"
            model_list += f"  - 摘要: {digest}\n"
            model_list += f"  - 模型家族: {family}\n"
            model_list += f"  - 参数量: {parameter_size}\n"
            model_list += f"  - 量化级别: {quantization_level}\n"
            model_list += f"  - 格式: {format_type}\n\n"

        print_info("可用的本地模型:")
        rprint(Panel(model_list.strip(), title="模型列表"))
    else:
        print_error("未能获取模型列表，请检查连接或权限。")

def human_readable_size(size_in_bytes):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_in_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.2f} {units[unit_index]}"

def show_model_info(url):
    model_name = Prompt.ask("请输入要查看的模型名称").strip()
    if not model_name:
        print_error("模型名称不能为空。")
        return

    result = call_ollama_api(url, "show", method="POST", json_data={"model": model_name})
    if result:
        info_text = ""
        for key, value in result.items():
            info_text += f"- [bold]{key}[/bold]: {safe_print(value)}\n"
        rprint(Panel(info_text.strip(), title=f"模型 [{model_name}] 的详细信息"))
    else:
        print_error("未能获取模型信息，请检查模型名称或连接。")

def generate_text(url):
    model_name = Prompt.ask("请输入模型名称").strip()
    prompt = Prompt.ask("请输入提示文本").strip()

    if not model_name or not prompt:
        print_error("模型名称和提示文本均不能为空。")
        return

    api_url = f"{url}/api/generate"
    headers = {"Content-Type": "application/json"}
    json_data = {"model": model_name, "prompt": prompt}

    try:
        generated_text = ""  
        complete_data = []  

        with requests.post(api_url, headers=headers, json=json_data, stream=True) as response:
            if response.status_code != 200:
                print_error(f"API 请求失败，状态码: {response.status_code}")
                return
            for line in response.iter_lines(decode_unicode=True):
                if line:  
                    try:
                        event = json.loads(line)
                        complete_data.append(event) 
                        if "response" in event:
                            generated_text += event["response"] 
                        if event.get("done", False): 
                            break
                    except json.JSONDecodeError:
                        print(f"无法解析事件: {line}")

        print_info(json.dumps(complete_data, indent=4, ensure_ascii=False))
        if generated_text.strip():
            rprint(Panel(f"[bold green]{generated_text.strip()}[/bold green]", title="生成的文本"))
        else:
            print_error("生成的文本为空，请尝试其他提示文本。")

    except requests.exceptions.RequestException as e:
        print_error(f"请求过程中发生错误: {e}")

def delete_model(url):
    model_name = Prompt.ask("请输入要删除的模型名称").strip()
    if not model_name:
        print_error("模型名称不能为空。")
        return

    confirm = Confirm.ask(f"确定要删除模型 [bold cyan]{model_name}[/bold cyan] 吗?")
    if not confirm:
        print_info("操作已取消。")
        return

    result = call_ollama_api(url, "delete", method="DELETE", json_data={"model": model_name})
    if result == "":
        print_info("模型删除成功！")
    else:
        print_error("模型删除失败，请检查模型名称或连接。")

def pull_model(url):
    model_name = Prompt.ask("请输入要下载的模型名称").strip()
    if not model_name:
        print_error("模型名称不能为空。")
        return

    stream = Confirm.ask("是否启用流式传输?", default=False)
    result = call_ollama_api(url, "pull", method="POST", json_data={"model": model_name, "stream": stream})
    if result is True:
        print_info("模型下载成功！")
    else:
        print_error("模型下载失败，请检查模型名称或网络连接。")

def push_model(url):
    model_name = Prompt.ask("请输入要上传的模型名称").strip()
    if not model_name:
        print_error("模型名称不能为空。")
        return

    stream = Confirm.ask("是否启用流式传输?", default=False)
    result = call_ollama_api(url, "push", method="POST", json_data={"model": model_name, "stream": stream})
    if result is True:
        print_info("模型上传成功！")
    else:
        print_error("模型上传失败，请检查模型名称或网络连接。")

def check_blob(url):
    digest = Prompt.ask("请输入文件的 SHA256 摘要").strip()
    if not digest:
        print_error("SHA256 摘要不能为空。")
        return

    response = requests.head(f"{url}/api/blobs/{digest}", verify=False)
    if response.status_code == 200:
        print_info("Blob 文件存在！")
    elif response.status_code == 404:
        print_error("Blob 文件不存在！")
    else:
        print_error(f"检查失败，状态码: {response.status_code}")

def copy_model(url):
    source_model = Prompt.ask("请输入源模型名称").strip()
    target_model = Prompt.ask("请输入目标模型名称").strip()
    if not source_model or not target_model:
        print_error("源模型和目标模型名称均不能为空。")
        return

    result = call_ollama_api(url, "copy", method="POST", json_data={"from": source_model, "to": target_model})
    if result is True:
        print_info("模型复制成功！")
    else:
        print_error("模型复制失败，请检查模型名称或连接。")
def main():
    console.clear()

    header = custom_header("Ollama API T00l", "https://github.com/Team-intN18-SoybeanSeclab/OllamaT00l")
    print_info("当您打开此工具时，意味着您已阅读并同意免责声明。")
    rprint(header)

    ollama_url = Prompt.ask("请输入 Ollama API URL").strip()
    if ollama_url.endswith("/"):
        ollama_url = ollama_url[:-1]
    if not ollama_url:
        print_error("API URL 不能为空。")
        return
    while True:
        rprint("[1] 列出所有本地模型")
        rprint("[2] 显示模型详细信息")
        rprint("[3] 生成文本")
        rprint("[4] 复制模型")
        rprint("[5] 删除模型")
        rprint("[6] 下载模型")
        rprint("[7] 上传模型")
        rprint("[8] 检查 Blob 文件")
        rprint("[0] 退出程序")

        choice = Prompt.ask("\n请输入选项").strip().lower()

        if choice == "1":
            list_models(ollama_url)
        elif choice == "2":
            show_model_info(ollama_url)
        elif choice == "3":
            generate_text(ollama_url)
        elif choice == "4":
            copy_model(ollama_url)
        elif choice == "5":
            delete_model(ollama_url)
        elif choice == "6":
            pull_model(ollama_url)
        elif choice == "7":
            push_model(ollama_url)
        elif choice == "8":
            check_blob(ollama_url)
        elif choice == "0":
            print_info("感谢使用，再见！")
            break
        else:
            print_error("无效的选项，请重新选择。")

if __name__ == "__main__":
    main()
