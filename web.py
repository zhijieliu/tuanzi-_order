import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import os
import io

# --- 页面基础配置 ---
st.set_page_config(
    page_title="团子订单生成器",
    page_icon="🧾",
    layout="wide"
)

# --- Matplotlib 字体配置 ---
import matplotlib.font_manager as fm
FONT_PATH = 'simhei.ttf'
if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    plt.rcParams['font.sans-serif'] = ['SimHei']
else:
    st.warning("SimHei 字体文件 (simhei.ttf) 未找到，请确保它和 webapp.py 在同一目录下。中文可能显示为方框。")
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# --- 核心数据和常量 ---
COLUMN_CONFIG = {
    "sn":      {"text": "S.N.",      "weight": 1, "anchor": "center"},
    "image":   {"text": "图片",      "weight": 2.5, "anchor": "center"},
    "desc":    {"text": "商品名称",  "weight": 5, "anchor": "w"},
    "price":   {"text": "单价(RMB)","weight": 2, "anchor": "center"},
    "qty":     {"text": "数量(套)",  "weight": 1.5, "anchor": "center"},
    "total":   {"text": "总价",      "weight": 2, "anchor": "center"},
}

# --- 初始化会话状态 ---
if 'data' not in st.session_state:
    st.session_state.data = [
        # 【核心修正】不再存储文件路径，而是存储图片二进制数据
        {"S.N.": 1, "商品名称": "黑色钢琴玩偶(KAKA)", "单价(RMB)": 69.0, "数量(套)": 5, "图片数据": None},
        {"S.N.": 2, "商品名称": "黄色钢琴玩偶(YUki)", "单价(RMB)": 59.0, "数量(套)": 5, "图片数据": None},
        {"S.N.": 3, "商品名称": "大提琴地毯", "单价(RMB)": 89.0, "数量(套)": 5, "图片数据": None},
    ]
if 'tax_rate' not in st.session_state:
    st.session_state.tax_rate = 0.01
if 'shipping_fee' not in st.session_state:
    st.session_state.shipping_fee = 0.0

# --- 核心函数 ---
def update_totals():
    for item in st.session_state.data:
        try:
            item['总价'] = float(item.get('单价(RMB)', 0)) * int(item.get('数量(套)', 0))
        except (ValueError, TypeError):
            item['总价'] = 0.0

def generate_table_image():
    update_totals()
    
    headers = [cfg["text"] for cfg in COLUMN_CONFIG.values()]
    cell_data = []
    for item in st.session_state.data:
        cell_data.append([
            item["S.N."], "", item["商品名称"], f'{item.get("单价(RMB)", 0.0):.2f}',
            item.get("数量(套)", 0), f'{item.get("总价", 0.0):.2f}'
        ])

    subtotal = sum(item.get('总价', 0) for item in st.session_state.data)
    tax = subtotal * st.session_state.tax_rate
    grand_total = subtotal + tax + st.session_state.shipping_fee

    summary_rows = [
        {"label": f"税价 ({st.session_state.tax_rate:.0%})", "value": f"{tax:.2f}"},
        {"label": "运费", "value": f'{st.session_state.shipping_fee:.2f}'},
        {"label": "总计", "value": f"{grand_total:,.2f}"}
    ]
    for row in summary_rows:
        cell_data.append(["", "", "", "", row["label"], row["value"]])

    num_data_rows = len(st.session_state.data)
    fig_height_inches = (len(cell_data) + 1) * 0.6
    fig, ax = plt.subplots(figsize=(12, fig_height_inches), dpi=300)
    ax.axis('off')

    col_widths = [cfg["weight"] / sum(c["weight"] for c in COLUMN_CONFIG.values()) for cfg in COLUMN_CONFIG.values()]
    table = ax.table(cellText=cell_data, colLabels=headers, loc='center', cellLoc='center', colWidths=col_widths)
    table.auto_set_font_size(False); table.set_fontsize(10)
    
    align_map = {'w': 'left', 'e': 'right', 'center': 'center'}
    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor('#cccccc'); cell.set_height(0.6 / fig_height_inches)
        col_id = list(COLUMN_CONFIG.keys())[j]
        anchor = COLUMN_CONFIG.get(col_id, {}).get("anchor", "center")
        ha_align = align_map.get(anchor, 'left')
        if i == 0: cell.set_facecolor('#f0f0f0'); cell.set_text_props(weight='bold', ha=ha_align)
        elif i > num_data_rows:
            cell.set_facecolor('#fafafa')
            if j < 4: cell.set_edgecolor('#fafafa'); cell.get_text().set_color('#fafafa')
            elif j == 4: cell.set_edgecolor('#fafafa'); cell.set_text_props(ha='right', va='center', weight='bold', color='#003366')
            else: cell.set_text_props(weight='bold', ha='center')
        else: cell.set_text_props(ha=ha_align, va='center')

    fig.canvas.draw()
    for i, item in enumerate(st.session_state.data):
        # 【核心修正】直接从 session_state 读取图片二进制数据
        img_bytes = item.get("图片数据")
        if img_bytes:
            try:
                img = Image.open(io.BytesIO(img_bytes))
                img.thumbnail((50, 50), Image.LANCZOS)
                im_offset = OffsetImage(img, zoom=1)
                cell = table.get_celld()[(i + 1, 1)]
                bbox = cell.get_bbox()
                cell_center = (bbox.x0 + bbox.width / 2, bbox.y0 + bbox.height / 2)
                ab = AnnotationBbox(im_offset, cell_center, xycoords='axes fraction', box_alignment=(0.5, 0.5), frameon=False, pad=0)
                ax.add_artist(ab)
            except Exception as e:
                st.error(f"生成图片时出错: {e}")

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300, pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return buf

# --- Streamlit 界面布局 ---

st.title("🧾 团子订单生成器 (网页版)")
st.markdown("您可以直接在下面的表格中编辑商品信息，并通过下方的上传工具为指定商品添加图片。")

# 【核心修正】为了让更新更流畅，我们将 DataFrame 的创建和编辑分开
# 创建一个可供 data_editor 使用的 DataFrame，并移除图片数据列
df_for_editor = pd.DataFrame(st.session_state.data).drop(columns=['图片数据'])

edited_df = st.data_editor(
    df_for_editor,
    use_container_width=True,
    num_rows="dynamic",
    key="data_editor"
)

# 当表格编辑后，将数据合并回 session_state
if edited_df is not None:
    # 创建一个查找字典以便合并图片数据
    img_data_map = {item['S.N.']: item.get('图片数据') for item in st.session_state.data}
    
    st.session_state.data = edited_df.to_dict('records')
    for i, item in enumerate(st.session_state.data):
        item["S.N."] = i + 1
        # 重新关联图片数据
        item["图片数据"] = img_data_map.get(item["S.N."])

# 每次脚本运行时都更新总价
update_totals()

st.divider()

# --- 图片上传区域 ---
st.subheader("📷 上传图片")
if not st.session_state.data:
    st.warning("请先在上方表格中添加商品行。")
else:
    product_options = [f'{item["S.N."]}. {item["商品名称"]}' for item in st.session_state.data]
    selected_product_str = st.selectbox("选择要上传图片的商品:", product_options, key="product_selector")
    
    uploaded_file = st.file_uploader("点击此处上传图片...", type=["png", "jpg", "jpeg", "gif"], key="file_uploader")

    if uploaded_file is not None and selected_product_str:
        selected_index = product_options.index(selected_product_str)
        
        # 【核心修正】直接将二进制数据存入 state
        st.session_state.data[selected_index]["图片数据"] = uploaded_file.getvalue()
        
        st.success(f"图片已成功关联到: {selected_product_str}")
        st.image(uploaded_file, caption="上传预览", width=100) # 显示一个预览
        
        # 【核心修正】移除 st.rerun()，让 Streamlit 自然更新

st.divider()

# --- 汇总和下载区域 ---
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("💰 最终账单汇总")
    subtotal = sum(item.get('总价', 0) for item in st.session_state.data)
    tax = subtotal * st.session_state.tax_rate
    shipping_fee = st.session_state.get('shipping_fee', 0.0) # 安全获取
    grand_total = subtotal + tax + shipping_fee
    
    st.metric("商品总计", f"¥ {subtotal:,.2f}")
    st.metric(f"税价 ({st.session_state.tax_rate:.0%})", f"¥ {tax:,.2f}")
    st.metric("运费", f"¥ {shipping_fee:,.2f}")
    st.metric("最终总计", f"¥ {grand_total:,.2f}", delta="CNY")

with col2:
    st.subheader("⚙️ 设置与操作")
    st.session_state.shipping_fee = st.number_input("输入运费", value=st.session_state.shipping_fee, min_value=0.0, step=1.0)
    
    # 按钮被点击时，会重新运行脚本，generate_table_image() 会被调用
    st.download_button(
        "📥 生成并下载表格图片",
        generate_table_image(),
        "commodity_table.png",
        "image/png"
    )
