# 卡密管理系统

基于 Netlify Functions + Supabase 的卡密授权管理系统。

## 功能

- 卡密验证API（exe调用）
- 批量生成卡密（月卡/季卡/年卡/永久卡）
- 卡密列表管理（搜索、筛选、分页）
- 卡密操作（封禁、解封、重置机器码、延长有效期、删除）
- 数据统计面板
- 机器码绑定（一卡一设备）
- 管理员密码保护

## API接口

### 1. 卡密验证（exe调用）
```
POST /api/verify-card
Body: { "card_code": "XXXX-XXXX-XXXX-XXXX", "machine_code": "设备唯一标识" }
```

返回：
- `code: 0` - 验证通过/激活成功
- `code: -1` - 卡密不存在
- `code: -2` - 卡密已被封禁
- `code: -3` - 首次激活需要机器码
- `code: -4` - 激活失败
- `code: -5` - 卡密已绑定其他设备
- `code: -6` - 卡密已过期

### 2. 批量生成卡密
```
POST /api/generate-cards
Body: { "count": 10, "card_type": "monthly", "duration_days": 30, "notes": "备注", "password": "管理员密码" }
```

### 3. 卡密列表
```
GET /api/list-cards?password=xxx&page=1&page_size=20&status=active&card_type=monthly&search=XXXX
```

### 4. 更新卡密
```
POST /api/update-card
Body: { "id": "卡密ID", "action": "ban|unban|reset_machine|extend|delete", "password": "管理员密码" }
```

### 5. 统计数据
```
GET /api/stats?password=xxx
```

## 部署步骤

### 1. 部署到Netlify
1. 登录 Netlify 后台
2. 点击 "Add new site" → "Deploy manually"
3. 把 `card-system` 文件夹拖拽到上传区域
4. 等待部署完成

### 2. 配置环境变量
1. 进入站点设置 → Site settings → Environment variables
2. 添加以下变量：
   - `SUPABASE_URL`: 你的Supabase项目URL
   - `SUPABASE_SERVICE_ROLE_KEY`: 你的Supabase service_role密钥
   - `ADMIN_PASSWORD`: 管理后台登录密码（默认: admin123，建议修改）

### 3. 重新部署
配置环境变量后，需要重新部署才能生效：
1. 进入 Deploys 页面
2. 点击最新部署右侧的三个点
3. 选择 "Retry deploy" → "Clear cache and retry deploy"

## 使用说明

### 管理后台
访问你的Netlify站点地址，输入管理员密码登录。

### exe对接
在你的程序中调用 `/api/verify-card` 接口验证卡密：

```python
import requests
import hashlib

def get_machine_code():
    """获取设备唯一标识"""
    import uuid
    return hashlib.md5(str(uuid.getnode()).encode()).hexdigest()

def verify_card(card_code):
    """验证卡密"""
    machine_code = get_machine_code()
    resp = requests.post(
        "https://你的站点.netlify.app/api/verify-card",
        json={"card_code": card_code, "machine_code": machine_code},
        timeout=10
    )
    result = resp.json()
    return result["code"] == 0, result.get("msg", ""), result
```

## 卡密类型

- `monthly` - 月卡（30天）
- `quarterly` - 季卡（90天）
- `yearly` - 年卡（365天）
- `permanent` - 永久卡（无过期时间）

## 卡密状态

- `inactive` - 未激活（未使用）
- `active` - 已激活（正常使用中）
- `expired` - 已过期
- `banned` - 已封禁
