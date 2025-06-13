const app = getApp();
const baseUrl = app.globalData.baseUrl;
Page({
  data: {
    statistics: [], // 统计数据
    loading: false, // 加载状态
    startDate: '', // 起始日期
    endDate: '', // 终止日期
    analysis: {
      markdownContent: {}
    }
  },
  onLoad: function() {
    const today = this.formatDate(new Date());
    this.setData({ 
      startDate: today,
      endDate: today 
    });
    this.fetchStatistics();
  },
  // 获取统计数据
  fetchStatistics: function() {
    this.setData({ loading: true });
    wx.request({
      url: `${baseUrl}/admin/statistics`,
      method: 'GET',
      data: { 
        start_date: this.data.startDate,
        end_date: this.data.endDate 
      },
      header: {
        'Authorization': 'Bearer ' + app.globalData.accessToken,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.data.statistics) {
          this.setData({ 
            statistics: res.data.statistics,
            analysis: res.data.analysis || {}
          });
        } else {
          // 处理数据格式错误
          wx.showToast({
            title: '数据格式错误',
            icon: 'none'
          });
        }
        // 在获取AI分析结果后添加
        if (res.data.analysis) {
          const mdContent = res.data.analysis.suggestions || '';
          const markdownObj = app.towxml(mdContent, 'markdown', {
            theme: 'light',
            events: {
              tap: e => console.log('tap', e)
            }
          });
          this.setData({
            'analysis.markdownContent': markdownObj
          });
        }
      },
      fail: (err) => {
        // 处理请求失败
        wx.showToast({
          title: '请求失败: ' + err.errMsg,
          icon: 'none'
        });
      },
      complete: () => {
        this.setData({ loading: false });
      }
    });
  },
  // 日期变化处理
  onStartDateChange(e) {
    this.setData({ startDate: e.detail.value });
    this.fetchStatistics();
  },
  onEndDateChange(e) {
    this.setData({ endDate: e.detail.value });
    this.fetchStatistics();
  },
})