# last updated: 2025-06-03
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io
import tempfile
import os

def parse_uploaded_files(uploaded_files):
    """アップロードされたCSVファイルを解析"""
    
    all_data = []
    tag_histories = {}
    
    # ファイルを日時順にソート
    file_data = []
    for uploaded_file in uploaded_files:
        content = uploaded_file.read().decode('utf-8')
        file_data.append({
            'name': uploaded_file.name,
            'content': content
        })
    
    # ファイル名でソート（タイムスタンプが含まれている前提）
    file_data.sort(key=lambda x: x['name'])
    
    for file_info in file_data:
        try:
            filename = file_info['name']
            content = file_info['content'].strip()
            
            if not content:
                continue
                
            lines = content.split('\n')
            headers = lines[0].split(',')
            
            if len(headers) < 4:
                continue
                
            timestamp = headers[0]
            sequence = headers[3]
            data_rows = lines[1:]
            
            # タイムスタンプを整形
            try:
                dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                formatted_time = dt.strftime('%Y/%m/%d %H:%M:%S')
            except:
                formatted_time = timestamp
            
            # タグIDを抽出
            tag_ids = []
            for row in data_rows:
                if row.strip():
                    columns = row.split(',')
                    if len(columns) > 4 and columns[4]:
                        tag_id = columns[4].replace('\r', '')
                        tag_ids.append(tag_id)
                        
                        # タグ履歴を記録
                        if tag_id not in tag_histories:
                            tag_histories[tag_id] = []
                        tag_histories[tag_id].append({
                            'timestamp': formatted_time,
                            'datetime': dt,
                            'sequence': sequence,
                            'filename': filename
                        })
            
            all_data.append({
                'filename': filename,
                'timestamp': formatted_time,
                'datetime': dt,
                'sequence': sequence,
                'tag_count': len(tag_ids),
                'tag_ids': tag_ids,
                'raw_timestamp': timestamp
            })
            
        except Exception as e:
            st.warning(f"ファイル {filename} の読み込みでエラー: {e}")
            continue
    
    return all_data, tag_histories

def parse_sample_data():
    """サンプルデータを生成（デモ用）"""
    sample_data = [
        {'filename': 'sample1.csv', 'timestamp': '2025/02/18 07:44:06', 'sequence': '00', 'tag_count': 0, 'tag_ids': []},
        {'filename': 'sample2.csv', 'timestamp': '2025/02/18 08:05:01', 'sequence': '01', 'tag_count': 0, 'tag_ids': []},
        {'filename': 'sample3.csv', 'timestamp': '2025/02/18 08:05:34', 'sequence': '02', 'tag_count': 1, 'tag_ids': ['A0250212154400343032353031303330']},
        {'filename': 'sample4.csv', 'timestamp': '2025/02/18 08:05:43', 'sequence': '03', 'tag_count': 2, 'tag_ids': ['A0250212154400343032353031303330', 'A025021310432700323032353032313030363031']},
        {'filename': 'sample5.csv', 'timestamp': '2025/02/18 08:05:48', 'sequence': '04', 'tag_count': 3, 'tag_ids': ['A0250212153633343032353031303236', 'A0250212154400343032353031303330', 'A025021310432700323032353032313030363031']},
    ]
    
    tag_histories = {}
    for data in sample_data:
        dt = datetime.strptime(data['timestamp'], '%Y/%m/%d %H:%M:%S')
        data['datetime'] = dt
        
        for tag_id in data['tag_ids']:
            if tag_id not in tag_histories:
                tag_histories[tag_id] = []
            tag_histories[tag_id].append({
                'timestamp': data['timestamp'],
                'datetime': dt,
                'sequence': data['sequence'],
                'filename': data['filename']
            })
    
    return sample_data, tag_histories

def get_sequence_info(seq):
    """シーケンス情報を取得"""
    sequence_map = {
        '00': {'label': '待機中', 'color': '#6B7280', 'bg_color': '#F3F4F6'},
        '01': {'label': '初期化', 'color': '#2563EB', 'bg_color': '#DBEAFE'},
        '02': {'label': '加工準備', 'color': '#D97706', 'bg_color': '#FEF3C7'},
        '03': {'label': '加工中', 'color': '#EA580C', 'bg_color': '#FED7AA'},
        '04': {'label': '加工完了', 'color': '#16A34A', 'bg_color': '#DCFCE7'}
    }
    return sequence_map.get(seq, {'label': '不明', 'color': '#DC2626', 'bg_color': '#FEE2E2'})

def calculate_sequence_stats(data):
    """シーケンス別統計を計算"""
    if not data:
        return {}
    
    df = pd.DataFrame(data)
    df = df.sort_values('datetime')
    
    stats = {}
    
    for seq in ['00', '01', '02', '03', '04']:
        seq_data = df[df['sequence'] == seq]
        count = len(seq_data)
        
        # 継続時間を計算
        total_duration = 0
        if count > 0:
            for i in range(len(df)):
                if df.iloc[i]['sequence'] == seq and i < len(df) - 1:
                    duration = (df.iloc[i+1]['datetime'] - df.iloc[i]['datetime']).total_seconds() / 60
                    total_duration += duration
        
        stats[seq] = {
            'count': count,
            'percentage': (count / len(df) * 100) if len(df) > 0 else 0,
            'total_duration': total_duration,
            'avg_duration': total_duration / count if count > 0 else 0
        }
    
    # 時間の割合を計算
    total_time = sum(stat['total_duration'] for stat in stats.values())
    for seq in stats:
        stats[seq]['time_percentage'] = (stats[seq]['total_duration'] / total_time * 100) if total_time > 0 else 0
    
    return stats

def main():
    st.set_page_config(
        page_title="RFID加工機監視ダッシュボード",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📊 RFID加工機監視ダッシュボード")
    st.markdown("---")
    
    # サイドバーでファイルアップロード
    st.sidebar.header("📁 データソース")
    
    # ファイルアップロード
    uploaded_files = st.sidebar.file_uploader(
        "CSVファイルを選択してください",
        type=['csv'],
        accept_multiple_files=True,
        help="複数のCSVファイルを同時に選択できます"
    )
    
    # デモデータオプション
    use_demo_data = st.sidebar.checkbox("デモデータを使用", help="サンプルデータでダッシュボードをテストできます")
    
    # データソースの選択
    if uploaded_files:
        st.sidebar.success(f"✅ {len(uploaded_files)}個のファイルがアップロードされました")
        with st.spinner("データを解析中..."):
            data, tag_histories = parse_uploaded_files(uploaded_files)
    elif use_demo_data:
        st.sidebar.info("🎯 デモデータを使用中")
        data, tag_histories = parse_sample_data()
    else:
        st.sidebar.warning("⚠️ CSVファイルをアップロードしてください")
        
        # 使用方法の説明
        st.markdown("""
        ## 📖 使用方法
        
        1. **サイドバー**からCSVファイルをアップロードしてください
        2. 複数のファイルを同時に選択可能です
        3. または「**デモデータを使用**」にチェックを入れてサンプルデータをお試しください
        
        ### CSVファイル形式
        ```
        20250218080534,0001,6C,02,A0250212154136343032353031303235
        20250218080534,0001,6C,02,A0250212154400343032353031303330
        ```
        
        - **列1**: タイムスタンプ (YYYYMMDDhhmmss)
        - **列2**: 固定値 (0001)
        - **列3**: 固定値 (6C)
        - **列4**: シーケンス番号 (00-04)
        - **列5**: RFIDタグID
        """)
        return
    
    if not data:
        st.error("❌ 有効なデータが見つかりません。CSVファイルの形式を確認してください。")
        return
    
    # データ概要
    st.sidebar.markdown("### 📊 データ概要")
    st.sidebar.metric("ファイル数", len(set(item['filename'] for item in data)))
    st.sidebar.metric("レコード数", len(data))
    st.sidebar.metric("ユニークタグ数", len(tag_histories))
    
    # 現在の状況
    latest = data[-1] if data else {}
    
    st.header("🔄 現在の状況")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        current_seq = latest.get('sequence', '00')
        seq_info = get_sequence_info(current_seq)
        st.metric("現在のシーケンス", current_seq)
        st.markdown(f"<div style='background-color: {seq_info['bg_color']}; color: {seq_info['color']}; padding: 8px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 5px;'>{seq_info['label']}</div>", unsafe_allow_html=True)
    
    with col2:
        st.metric("検出中のタグ数", latest.get('tag_count', 0))
    
    with col3:
        st.metric("総タグ数", len(tag_histories))
    
    with col4:
        st.metric("最終更新", latest.get('timestamp', 'No data'))
    
    st.markdown("---")
    
    # シーケンス別稼働状況
    st.header("📈 シーケンス別稼働状況")
    
    seq_stats = calculate_sequence_stats(data)
    
    # 稼働状況の可視化
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 稼働統計")
        stats_data = []
        for seq, stats in seq_stats.items():
            seq_info = get_sequence_info(seq)
            stats_data.append({
                'シーケンス': f"{seq}",
                'ステータス': seq_info['label'],
                '出現回数': stats['count'],
                '出現率(%)': f"{stats['percentage']:.1f}",
                '総時間(分)': f"{stats['total_duration']:.1f}",
                '平均時間(分)': f"{stats['avg_duration']:.1f}",
                '時間割合(%)': f"{stats['time_percentage']:.1f}"
            })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🥧 時間割合")
        
        # 円グラフ
        labels = [f"seq={seq}<br>{get_sequence_info(seq)['label']}" for seq in seq_stats.keys()]
        values = [stats['time_percentage'] for stats in seq_stats.values()]
        colors = [get_sequence_info(seq)['color'] for seq in seq_stats.keys()]
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            hole=0.3
        )])
        fig_pie.update_layout(
            title="シーケンス別時間割合",
            showlegend=True,
            height=400
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # 全体サマリー
    st.subheader("📋 全体サマリー")
    col1, col2, col3, col4 = st.columns(4)
    
    working_time = seq_stats.get('03', {}).get('total_duration', 0) + seq_stats.get('04', {}).get('total_duration', 0)
    waiting_time = seq_stats.get('00', {}).get('total_duration', 0) + seq_stats.get('01', {}).get('total_duration', 0)
    total_time = sum(stats['total_duration'] for stats in seq_stats.values())
    efficiency = (working_time / total_time * 100) if total_time > 0 else 0
    
    with col1:
        st.metric("総計測回数", len(data), help="全データレコード数")
    with col2:
        st.metric("加工中時間", f"{working_time:.1f}分", help="seq=03,04の合計時間")
    with col3:
        st.metric("待機時間", f"{waiting_time:.1f}分", help="seq=00,01の合計時間")
    with col4:
        st.metric("稼働効率", f"{efficiency:.1f}%", help="加工中時間の割合")
    
    st.markdown("---")
    
    # 現在検出中のタグ
    if latest.get('tag_ids'):
        st.header("🏷️ 現在検出中のタグ")
        
        # タグをカードスタイルで表示
        cols = st.columns(min(3, len(latest['tag_ids'])))
        for i, tag_id in enumerate(latest['tag_ids']):
            with cols[i % 3]:
                display_tag = tag_id[:8] + "..." + tag_id[-8:] if len(tag_id) > 20 else tag_id
                st.success(f"🏷️ **タグ {i+1}**\n\n`{display_tag}`")
        
        st.markdown("---")
    
    # タグ履歴とログを2列で表示
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("📋 タグ履歴")
        
        if tag_histories:
            # 検出回数でソート
            sorted_tags = sorted(tag_histories.items(), key=lambda x: len(x[1]), reverse=True)
            
            for tag_id, history in sorted_tags[:5]:  # 上位5個のタグを表示
                with st.expander(f"🏷️ {tag_id[:8]}...{tag_id[-8:]} ({len(history)}回検出)"):
                    history_df = pd.DataFrame(history)
                    history_df = history_df.sort_values('datetime', ascending=False)
                    
                    # 最近の履歴を表示
                    recent_history = history_df.head(10)[['timestamp', 'sequence']].copy()
                    recent_history['ステータス'] = recent_history['sequence'].apply(lambda x: get_sequence_info(x)['label'])
                    recent_history.columns = ['時刻', 'seq', 'ステータス']
                    st.dataframe(recent_history, use_container_width=True, hide_index=True)
        else:
            st.info("タグ履歴がありません")
    
    with col2:
        st.header("⏰ 時系列ログ")
        
        # 最新20件を表示
        if len(data) > 0:
            df_display = pd.DataFrame(data[-20:])
            df_display = df_display.sort_values('datetime', ascending=False)
            df_display['ステータス'] = df_display['sequence'].apply(lambda x: get_sequence_info(x)['label'])
            df_display_clean = df_display[['timestamp', 'sequence', 'ステータス', 'tag_count']].copy()
            df_display_clean.columns = ['時刻', 'seq', 'ステータス', 'タグ数']
            st.dataframe(df_display_clean, use_container_width=True, hide_index=True)
        else:
            st.info("ログデータがありません")
    
    st.markdown("---")
    
    # 時系列グラフ
    st.header("📊 時系列グラフ")
    
    if len(data) > 1:
        df_chart = pd.DataFrame(data)
        df_chart['sequence_num'] = df_chart['sequence'].astype(int)
        
        # シーケンス推移
        fig = px.line(
            df_chart, 
            x='datetime', 
            y='sequence_num',
            title='シーケンス推移',
            labels={'sequence_num': 'シーケンス', 'datetime': '時刻'},
            markers=True
        )
        fig.update_layout(yaxis=dict(tickmode='array', tickvals=[0, 1, 2, 3, 4]))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # タグ数推移
        fig2 = px.bar(
            df_chart, 
            x='datetime', 
            y='tag_count',
            title='検出タグ数推移',
            labels={'tag_count': 'タグ数', 'datetime': '時刻'},
            color='tag_count',
            color_continuous_scale='viridis'
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("グラフ表示には2つ以上のデータポイントが必要です")
    
    # フッター
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>📊 RFID加工機監視ダッシュボード | Built with Streamlit</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
