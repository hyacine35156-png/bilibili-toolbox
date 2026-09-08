// 统计数据API
const { supabaseRequest } = require('./lib/supabase');

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';

exports.handler = async (event, context) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
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

    // 获取所有卡密（用于统计）
    const { data: allCards } = await supabaseRequest('GET', 'cards', {
      select: 'status,card_type'
    });

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
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ code: -99, msg: '服务器错误: ' + error.message })
    };
  }
};
