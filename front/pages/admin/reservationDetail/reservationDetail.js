// pages/admin/reservationDetail/reservationDetail.js
const app = getApp();  // 获取小程序实例
const baseUrl = app.globalData.baseUrl;  // 基础API地址

Page({

  /**
   * 页面的初始数据
   */
  data: {
    statistics: [], // 统计数据
    loading: false, // 加载状态
    startDate: '', // 起始日期
    endDate: '', // 终止日期
  },

  // 添加日期格式化方法
  formatDate(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`; // 返回YYYY-MM-DD格式
  },

  onLoad() {
      const today = this.formatDate(new Date());
      this.setData({ 
        startDate: today,
        endDate: today 
      });
      this.fetchStatistics();
  },

  // 获取统计数据
  fetchStatistics() {
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