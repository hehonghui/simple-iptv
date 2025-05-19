import re
import requests
import time

def fetch_raw_m3u(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def test_m3u8_speed(url, timeout=10):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout, stream=True)
        first_byte_time = time.time()

        if response.status_code != 200:
            return float('inf')  # 不合格

        # 读取一小块数据确保链接有效
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                break

        return (first_byte_time - start_time) * 1000  # TTFB 毫秒
    except:
        return float('inf')


def extract_entries(m3u_text, keywords):
    # # 提取匹配关键字的频道
    # entries = []
    # lines = m3u_text.strip().splitlines()
    # for i in range(len(lines)):
    #     if lines[i].startswith('#EXTINF') and any(k in lines[i] for k in keywords):
    #         if i + 1 < len(lines) and not lines[i + 1].startswith('#'):
    #             entries.append(lines[i])
    #             entries.append(lines[i + 1])
    # return entries

    # keyword -> list of (extinf_line, url_line)
    candidate_map = {key: [] for key in keywords}

    lines = m3u_text.strip().splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith('#EXTINF'):
            extinf = lines[i]
            if i + 1 < len(lines):
                url = lines[i + 1]
                for key in keywords:
                    if key in extinf:
                        candidate_map[key].append((extinf, url))
                        break
            i += 2
        else:
            i += 1

    final_entries = []
    for key, candidates in candidate_map.items():
        if not candidates:
            continue

        # 测速所有候选
        best = None
        best_ttfb = float('inf')
        for extinf, url in candidates:
            ttfb = test_m3u8_speed(url)
            print(f"测速中：[{key}] {url} -> TTFB: {ttfb:.0f}ms")
            if ttfb != float('inf') and ttfb < best_ttfb:
                best_ttfb = ttfb
                best = (extinf, url)

        if best:
            final_entries.extend(best)

    return final_entries


if __name__ == '__main__':
    # 1. 获取完整的 ipv6.m3u
    url_full = 'https://raw.githubusercontent.com/fanmingming/live/refs/heads/main/tv/m3u/ipv6.m3u'
    full_m3u = fetch_raw_m3u(url_full)
    combined_entries = full_m3u.strip().splitlines()

    # 2. 提取 BBC
    url_bbc = 'https://raw.githubusercontent.com/YueChan/Live/refs/heads/main/Global.m3u'
    bbc_m3u = fetch_raw_m3u(url_bbc)
    bbc_entries = extract_entries(bbc_m3u, ['BBC'])

    # 3. 提取指定频道
    url_zh = 'https://raw.githubusercontent.com/suxuang/myIPTV/refs/heads/main/ipv6.m3u'
    zh_m3u = fetch_raw_m3u(url_zh)
    zh_keywords = ['台视新闻', '中天新闻', '香港卫视', '民视新闻台']
    zh_entries = extract_entries(zh_m3u, zh_keywords)

    # 4. 合并所有条目
    combined_entries += bbc_entries + zh_entries

    # 5. 保存到 simple.m3u
    with open('simple.m3u', 'w', encoding='utf-8') as f:
        f.write('#EXTM3U x-tvg-url="https://live.fanmingming.cn/e.xml" catchup="append" catchup-source="?playseek=${('
                'b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n')
        for line in combined_entries:
            f.write(f"{line.strip()}\n")

    print("✅ simple.m3u 生成完成")
