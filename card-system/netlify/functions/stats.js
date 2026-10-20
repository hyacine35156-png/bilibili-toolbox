// 统计数据API
const { supabaseRequest } = require('./lib/supabase');

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD;

exports.handler = async (event, context) => {
  const headers = {
    'Access-Control-Allow-Origin': process.env.ALLOWED_ORIGIN || '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  if (!ADMIN_PASSWORD) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ code: -99, msg: '服务器配置错误' })
    };
  }

  try {
    let params;
    if (event.httpMethod === 'GET') {
      params = event.queryStringParameters || {};
    } else {
      params = JSON.parse(event.body || '{}');
    }

    const { password } = params;

    if (password !== ADMIN_PASSWORD) {
      return {
        statusCode: 403,
        headers,
        body: JSON.stringify({ code: -1, msg: '管理员密码错误' })
      };
    }

    // 分页拉取卡密用于统计（避免全量拉取超时）
    const PAGE_SIZE = 1000;
    let allCards = [];
    let page = 0;
    while (true) {
      const from = page * PAGE_SIZE;
      const to = from + PAGE_SIZE - 1;
      const { data } = await supabaseRequest('GET', 'cards', {
        select: 'status,card_type',
        range: [from, to]
      });
      if (!data || data.length === 0) break;
      allCards = allCards.concat(data);
      if (data.length < PAGE_SIZE) break;
      page++;
    }

    // 按状态统计
    const statusStats = {
      total: allCards.length,
      inactive: 0,
      active: 0,
      expired: 0,
      banned: 0
    };

    // 按类型统计
    const typeStats = {
      monthly: 0,
      quarterly: 0,
      yearly: 0,
      permanent: 0,
      trial: 0
    };

    for (const card of allCards) {
      if (statusStats[card.status] !== undefined) {
        statusStats[card.status]++;
      }
      if (typeStats[card.card_type] !== undefined) {
        typeStats[card.card_type]++;
      }
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        code: 0,
        msg: '统计成功',
        data: statusStats,
        status: statusStats,
        type: typeStats
      })
    };

  } catch (error) {
    console.error('stats error:', error.message);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ code: -99, msg: '服务器内部错误' })
    };
  }
};
