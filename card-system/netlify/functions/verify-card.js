// 卡密验证API - exe调用
const { supabaseRequest } = require('./lib/supabase');

// 简单内存级限流（每IP每分钟最多20次验证）
const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW = 60 * 1000; // 1分钟
const RATE_LIMIT_MAX = 20;

function checkRateLimit(ip) {
  const now = Date.now();
  const requests = rateLimitMap.get(ip) || [];
  const validRequests = requests.filter(t => now - t < RATE_LIMIT_WINDOW);
  if (validRequests.length >= RATE_LIMIT_MAX) {
    rateLimitMap.set(ip, validRequests);
    return false;
  }
  validRequests.push(now);
  rateLimitMap.set(ip, validRequests);
  return true;
}

exports.handler = async (event, context) => {
  const headers = {
    'Access-Control-Allow-Origin': process.env.ALLOWED_ORIGIN || '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  // 限流检查
  const clientIP = event.headers['x-forwarded-for'] || event.headers['client-ip'] || 'unknown';
  if (!checkRateLimit(clientIP)) {
    return {
      statusCode: 429,
      headers,
      body: JSON.stringify({ code: -10, msg: '请求过于频繁，请稍后再试' })
    };
  }

  try {
    const { card_code, machine_code } = JSON.parse(event.body);

    if (!card_code) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ code: -1, msg: '卡密不能为空' })
      };
    }

    // 查询卡密
    const { data: cards } = await supabaseRequest('GET', 'cards', {
      filters: { card_code: `eq.${card_code}` }
    });

    if (!cards || cards.length === 0) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ code: -1, msg: '卡密不存在' })
      };
    }

    const card = cards[0];

    // 检查状态
    if (card.status === 'banned') {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ code: -2, msg: '卡密已被封禁' })
      };
    }

    // 未激活的卡密，首次验证时激活
    if (card.status === 'inactive') {
      if (!machine_code) {
        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ code: -3, msg: '首次激活需要机器码' })
        };
      }

      const now = new Date();
      
      // 永久卡（duration_days=0 或 card_type=permanent）不设置过期时间
      const isPermanent = card.card_type === 'permanent' || card.duration_days === 0;
      const expiresAt = isPermanent ? null : new Date(now.getTime() + card.duration_days * 24 * 60 * 60 * 1000);

      const updateBody = {
        status: 'active',
        machine_code,
        activated_at: now.toISOString()
      };
      if (expiresAt) {
        updateBody.expires_at = expiresAt.toISOString();
      } else {
        updateBody.expires_at = null;
      }

      await supabaseRequest('PATCH', 'cards', {
        filters: { id: `eq.${card.id}` },
        body: updateBody
      });

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          code: 0,
          msg: '激活成功',
          card_type: card.card_type,
          expires_at: expiresAt ? expiresAt.toISOString() : null,
          remaining_days: isPermanent ? -1 : card.duration_days
        })
      };
    }

    // 已激活的卡密，校验机器码
    if (card.machine_code) {
      if (!machine_code) {
        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ code: -7, msg: '需要机器码' })
        };
      }
      if (card.machine_code !== machine_code) {
        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ code: -5, msg: '卡密已绑定其他设备' })
        };
      }
    } else if (machine_code && card.status === 'active') {
      // 已激活但未绑定机器码的卡密，首次验证时自动绑定
      await supabaseRequest('PATCH', 'cards', {
        filters: { id: `eq.${card.id}` },
        body: {
          machine_code,
          activated_at: new Date().toISOString()
        }
      });
    }

    // 检查是否过期
    if (card.expires_at) {
      const now = new Date();
      const expiresAt = new Date(card.expires_at);
      
      if (now > expiresAt) {
        // 更新状态为过期（如果还不是expired状态）
        if (card.status !== 'expired') {
          await supabaseRequest('PATCH', 'cards', {
            filters: { id: `eq.${card.id}` },
            body: { status: 'expired' }
          });
        }

        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ code: -6, msg: '卡密已过期' })
        };
      } else if (card.status === 'expired') {
        // 卡密已被延长（expires_at在未来），自动把状态改回active
        await supabaseRequest('PATCH', 'cards', {
          filters: { id: `eq.${card.id}` },
          body: { status: 'active' }
        });
      }

      // 计算剩余天数
      const remainingMs = expiresAt - now;
      const remainingDays = Math.ceil(remainingMs / (24 * 60 * 60 * 1000));

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          code: 0,
          msg: '验证通过',
          card_type: card.card_type,
          expires_at: card.expires_at,
          remaining_days: remainingDays
        })
      };
    }

    // 永久卡（没有过期时间）
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        code: 0,
        msg: '验证通过',
        card_type: card.card_type,
        expires_at: null,
        remaining_days: -1
      })
    };

  } catch (error) {
    console.error('verify-card error:', error.message);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ code: -99, msg: '服务器内部错误' })
    };
  }
};
