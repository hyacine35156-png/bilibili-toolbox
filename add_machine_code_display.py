FILE = r"C:\Users\15868\Doubao\chats\2026-08-29\new-chat\bilibili-danmaku-bot\card-system\public\index.html"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

# 1. 修改表头，添加设备码列
old_thead = '''        <thead>
          <tr>
            <th style="width:22%;">卡密号</th>
            <th style="width:10%;">类型</th>
            <th style="width:10%;">状态</th>
            <th style="width:16%;">到期时间</th>
            <th style="width:20%;">备注</th>
            <th style="width:22%;">操作</th>
          </tr>
        </thead>'''

new_thead = '''        <thead>
          <tr>
            <th style="width:18%;">卡密号</th>
            <th style="width:8%;">类型</th>
            <th style="width:8%;">状态</th>
            <th style="width:14%;">到期时间</th>
            <th style="width:14%;">绑定设备码</th>
            <th style="width:16%;">备注</th>
            <th style="width:22%;">操作</th>
          </tr>
        </thead>'''

if old_thead in content:
    content = content.replace(old_thead, new_thead)
    print("✓ 表头已修改，添加设备码列")
else:
    print("✗ 未找到旧表头")

# 2. 修改空数据提示的colspan
content = content.replace('<td colspan="6">', '<td colspan="7">')
print("✓ 空数据提示colspan已修改")

# 3. 修改渲染逻辑，添加设备码显示
old_render = '''              const notesEscaped = (card.notes || '').replace(/"/g, '&quot;').replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
              return `
              <tr>
                <td>
                  <div class="card-code-cell">
                    <span class="card-code">${card.card_code}</span>
                    <button class="copy-btn" onclick="copyCardCode('${card.card_code}', this)" title="复制卡密">📋</button>
                  </div>
                </td>
                <td><span class="type-badge">${typeMap[card.card_type] || card.card_type}</span></td>
                <td><span class="status-badge status-${card.status}">${statusMap[card.status] || card.status}</span></td>
                <td><span class="expire-info ${expireClass}">${expireText}</span></td>
                <td class="notes-cell ${card.notes ? '' : 'empty'}" title="${notesEscaped}">${card.notes || '—'}</td>'''

new_render = '''              const notesEscaped = (card.notes || '').replace(/"/g, '&quot;').replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
              const machineCodeText = card.machine_code ? 
                '<span class="machine-code" title="' + card.machine_code + '">' + card.machine_code.substring(0, 8) + '...' + card.machine_code.substring(card.machine_code.length - 8) + '</span>' +
                '<button class="copy-btn" onclick="copyMachineCode(\\'' + card.machine_code + '\\', this)" title="复制设备码">📋</button>' :
                '<span class="machine-code-unbound">未绑定</span>';
              return `
              <tr>
                <td>
                  <div class="card-code-cell">
                    <span class="card-code">${card.card_code}</span>
                    <button class="copy-btn" onclick="copyCardCode('${card.card_code}', this)" title="复制卡密">📋</button>
                  </div>
                </td>
                <td><span class="type-badge">${typeMap[card.card_type] || card.card_type}</span></td>
                <td><span class="status-badge status-${card.status}">${statusMap[card.status] || card.status}</span></td>
                <td><span class="expire-info ${expireClass}">${expireText}</span></td>
                <td><div class="machine-code-cell">${machineCodeText}</div></td>
                <td class="notes-cell ${card.notes ? '' : 'empty'}" title="${notesEscaped}">${card.notes || '—'}</td>'''

if old_render in content:
    content = content.replace(old_render, new_render)
    print("✓ 渲染逻辑已修改，添加设备码显示")
else:
    print("✗ 未找到旧渲染逻辑")

# 4. 添加复制设备码函数和样式
old_copy_func = '''    // 复制卡密
    function copyCardCode(code, btn) {'''

new_copy_func = '''    // 复制设备码
    function copyMachineCode(code, btn) {
      navigator.clipboard.writeText(code).then(() => {
        btn.textContent = '✓';
        btn.classList.add('copied');
        showToast('已复制设备码', 'success');
        setTimeout(() => { btn.textContent = '📋'; btn.classList.remove('copied'); }, 1500);
      }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = code;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btn.textContent = '✓';
        btn.classList.add('copied');
        showToast('已复制设备码', 'success');
        setTimeout(() => { btn.textContent = '📋'; btn.classList.remove('copied'); }, 1500);
      });
    }

    // 复制卡密
    function copyCardCode(code, btn) {'''

if old_copy_func in content:
    content = content.replace(old_copy_func, new_copy_func)
    print("✓ 已添加复制设备码函数")
else:
    print("✗ 未找到复制卡密函数位置")

# 5. 添加设备码相关CSS样式
old_css = '''    .card-code-cell {
      display: flex;
      align-items: center;
      gap: 8px;
    }'''

new_css = '''    .card-code-cell {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .machine-code-cell {
      display: flex;
      align-items: center;
      gap: 6px;
      font-family: monospace;
      font-size: 12px;
    }
    .machine-code {
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
    }
    .machine-code-unbound {
      color: #64748b;
      font-style: italic;
    }'''

if old_css in content:
    content = content.replace(old_css, new_css)
    print("✓ 已添加设备码CSS样式")
else:
    print("✗ 未找到card-code-cell CSS位置")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print("\n卡密管理后台修改完成！")
