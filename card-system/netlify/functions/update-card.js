// 卡密状态更新API
const { supabaseRequest } = require('./lib/supabase');

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';

exports.handler = async (event, context) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  try {
    const { id, card_code, action, password, extra_days, extra_hours, extra_minutes, notes } = JSON.parse(event.body);

    if (password !== ADMIN_PASSWORD) {
      return {
        statusCode: 403,
        headers,
        body: JSON.stringify({ code: -1, msg: '管理员密码错误' })
      };
    }

    if (!id && !card_code) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ code: -2, msg: '需要卡密ID或卡密号' })
      };
    }

    // 查询卡密
    let card;
    if (id) {
      const { data } = await supabaseRequest('GET', 'cards', {
        filters: { id: `eq.${id}` }
      });
      card = data?.[0];
    } else {
      const { data } = await supabaseRequest('GET', 'cards', {
        filters: { card_code: `eq.${card_code}` }
      });
      card = data?.[0];
    }

    if (!card) {
      return {
        statusCode: 404,
        headers,
        body: JSON.stringify({ code: -3, msg: '卡密不存在' })
      };
    }

    let updateBody = {};
    let msg = '';

    switch (action) {
      case 'ban':
        updateBody = { status: 'banned' };
        msg = '卡密已封禁';
        break;
      case 'unban': {
        // 解封后判断状态：有过期时间且未过期则active，否则inactive
        const now = new Date();
        const isExpired = card.expires_at && new Date(card.expires_at) < now;
        updateBody = { status: card.expires_at && !isExpired ? 'active' : 'inactive' };
        msg = '卡密已解封';
        break;
      }
      case 'reset_machine':
        updateBody = { machine_code: null };
        msg = '机器码已重置';
        break;
      case 'extend': {
        // 支持天/小时/分钟，至少指定一个
        const days = parseFloat(extra_days) || 0;
        const hours = parseFloat(extra_hours) || 0;
        const minutes = parseFloat(extra_minutes) || 0;
        const totalMs = (days * 24 * 60 + hours * 60 + minutes) * 60 * 1000;
        if (totalMs <= 0) {
          return {
            statusCode: 400,
            headers,
            body: JSON.stringify({ code: -4, msg: '需要指定延长时间（天/小时/分钟）' })
          };
        }
        // 如果卡密已过期，从现在开始延长；否则从到期时间开始延长
        const now = new Date();
        const currentExpiry = card.expires_at ? new Date(card.expires_at) : now;
        const baseTime = currentExpiry < now ? now : currentExpiry;
        const newExpiry = new Date(baseTime.getTime() + totalMs);
        // 延长后状态改为active（如果之前是expired）
        updateBody = { 
          expires_at: newExpiry.toISOString(), 
          status: card.status === 'expired' ? 'active' : card.status 
        };
        // 构造提示信息
        let extendMsg = '有效期已延长';
        const parts = [];
        if (days > 0) parts.push(`${days}天`);
        if (hours > 0) parts.push(`${hours}小时`);
        if (minutes > 0) parts.push(`${minutes}分钟`);
        msg = extendMsg + parts.join('');
        break;
      }
      case 'edit_notes':
        if (notes === undefined) {
          return {
            statusCode: 400,
            headers,
            body: JSON.stringify({ code: -6, msg: '需要备注内容' })
          };
        }
        updateBody = { notes: String(notes).substring(0, 500) };
        msg = '备注已更新';
        break;
      case 'delete':
        await supabaseRequest('DELETE', 'cards', {
          filters: { id: `eq.${card.id}` }
        });
        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({ code: 0, msg: '卡密已删除' })
        };
      default:
        return {
          statusCode: 400,
          headers,
          body: JSON.stringify({ code: -5, msg: '无效操作' })
        };
    }

    // 更新卡密
    await supabaseRequest('PATCH', 'cards', {
      filters: { id: `eq.${card.id}` },
      body: updateBody
    });

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ code: 0, msg })
    };

  } catch (error) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ code: -99, msg: '服务器错误: ' + error.message })
    };
  }
};
