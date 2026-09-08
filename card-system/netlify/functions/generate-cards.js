// 批量生成卡密API
const { supabaseRequest } = require('./lib/supabase');
const crypto = require('crypto');

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';

function generateCardCode() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code = '';
  for (let i = 0; i < 4; i++) {
    if (i > 0) code += '-';
    for (let j = 0; j < 4; j++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
  }
  return code;
}

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
    const { count, card_type, duration_days, notes, password } = JSON.parse(event.body);

    if (password !== ADMIN_PASSWORD) {
      return {
        statusCode: 403,
        headers,
        body: JSON.stringify({ code: -1, msg: '管理员密码错误' })
      };
    }

    if (!count || count < 1 || count > 1000) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ code: -2, msg: '数量必须在1-1000之间' })
      };
    }

    // 允许自定义卡密类型，不限制
    if (!card_type) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ code: -3, msg: '卡密类型不能为空' })
      };
    }

    let days = duration_days;
    if (card_type === 'permanent') {
      days = 0;
    } else if (days === undefined || days === null || days <= 0) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ code: -4, msg: '有效天数必须大于0' })
      };
    }

    // 生成卡密
    const cards = [];
    const generatedCodes = new Set();
    
    // 查询数据库中已有的卡密，避免重复
    const { data: existingCards } = await supabaseRequest('GET', 'cards', {
      select: 'card_code'
    });
    const existingCodes = new Set(existingCards.map(c => c.card_code));

    for (let i = 0; i < count; i++) {
      let code;
      let attempts = 0;
      do {
        code = generateCardCode();
        attempts++;
        // 防止无限循环
        if (attempts > 100) {
          throw new Error('生成唯一卡密失败，请减少生成数量');
        }
      } while (generatedCodes.has(code) || existingCodes.has(code));
      
      generatedCodes.add(code);
      cards.push({
        card_code: code,
        status: 'inactive',
        card_type,
        duration_days: days,
        notes: notes || null
      });
    }

    // 批量插入
    const { data } = await supabaseRequest('POST', 'cards', {
      body: cards
    });

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        code: 0,
        msg: `成功生成${data.length}个卡密`,
        count: data.length,
        cards: data
      })
    };

  } catch (error) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ code: -99, msg: '服务器错误: ' + error.message })
    };
  }
};
