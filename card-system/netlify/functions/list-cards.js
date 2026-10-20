// 卡密列表API
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

    const { password, status, card_type, search, page = 1, page_size = 50 } = params;

    if (password !== ADMIN_PASSWORD) {
      return {
        statusCode: 403,
        headers,
        body: JSON.stringify({ code: -1, msg: '管理员密码错误' })
      };
    }

    // 构建筛选条件
    const filters = {};
    if (status && status !== 'all') filters.status = `eq.${status}`;
    if (card_type && card_type !== 'all') filters.card_type = `eq.${card_type}`;
    if (search) filters.card_code = `ilike.%${search}%`;

    // 分页
    const from = (page - 1) * page_size;
    const to = from + page_size - 1;

    const { data, total } = await supabaseRequest('GET', 'cards', {
      filters,
      order: 'created_at.desc',
      range: [from, to],
      count: true
    });

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        code: 0,
        msg: '查询成功',
        data,
        total: total || 0,
        page: parseInt(page),
        page_size: parseInt(page_size),
        total_pages: Math.ceil((total || 0) / page_size)
      })
    };

  } catch (error) {
    console.error('list-cards error:', error.message);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ code: -99, msg: '服务器内部错误' })
    };
  }
};
