// pages/scan/scan.js
const app = getApp();
const baseUrl = app.globalData.baseUrl;
Page({

  onShow: function () {
    if (typeof this.getTabBar === 'function' &&  this.getTabBar()) {
    this.getTabBar().setData({
       selected: 0
      })
    }
  },

  /**
   * 页面的初始数据
   */
  data: {
    isLoading: false,  // 加载状态
    scanResult: null, // 扫码结果
    checkInInfo: null // 签到成功后的详细信息
  },

  scanCode: function() {
    this.setData({ 
      isLoading: true,
      checkInInfo: null  // 重置签到信息
    });
    
    wx.scanCode({
      onlyFromCamera: true,
      scanType: ['qrCode'],
      success: (res) => {
        console.log('扫码结果:', res.result);
        this.setData({ scanResult: res.result });
        
        // 在请求前后添加加载状态
        this.setData({ isLoading: true });
        wx.request({
          url: app.globalData.baseUrl + '/reservations/check-in/' + encodeURIComponent(res.result),
          method: 'POST',
          header: {
            'Authorization': 'Bearer ' + app.globalData.accessToken,
            'Content-Type': 'application/json'
          },
          success: (response) => {
            if (response.statusCode === 200) {
              this.setData({
                checkInInfo: {
                  id: response.data.reservation.id,  // 预约ID
                  userName: response.data.reservation.user_name,  // 用户姓名
                  seatNumber: response.data.seat_number  // 座位号
                }
              });
              console.log(checkInInfo);
              wx.showToast({
                title: response.data.message || '签到成功',
                icon: 'success',
                duration: 2000
              });
            } else {
              wx.showToast({
                title: response.data.error || '签到失败',
                icon: 'none',
                duration: 2000
              });
            }
          },
          complete: () => {
            this.setData({ isLoading: false });
          }
        });
      },
      fail: (err) => {
        console.error('扫码失败:', err);
        wx.showToast({
          title: '扫码失败: ' + (err.errMsg || '未知错误'),
          icon: 'none',
          duration: 2000
        });
        this.setData({ isLoading: false });  // 结束加载
      }
    });
  }
});