// pages/driver/driver-list/driver-list.js
const app = getApp();

// 获取司机班次列表
const getDriverSchedules = (date, status) => {
  return new Promise((resolve, reject) => {
    wx.showLoading({ title: '加载中...' });
    
    wx.request({
      url: `${app.globalData.baseUrl}/drivers/schedules`,
      method: 'GET',
      data: { date, status },
      header: {
        'Authorization': `Bearer ${app.globalData.accessToken}`,
         'Content-Type': 'application/json'
      },
      success: (res) => {
        wx.hideLoading(); // 隐藏加载状态
        if (res.statusCode === 200) {
          resolve(res.data); // 返回成功数据
        } else {
          wx.showToast({
            title: res.data.error || '获取班次列表失败',
            icon: 'none',
            duration: 2000
          });
          reject(res.data.error); // 返回错误信息
        }
      },
      fail: (err) => {
        wx.hideLoading();
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none',
          duration: 2000
        });
        reject(err); // 返回网络错误
      }
    });
  });
};

// 在Page中使用示例
Page({
  data: {
    driverName : app.globalData.userInfo?.user.name,
    driverId : app.globalData.userInfo?.user.school_id,
    schedules: [],
    isLoading: false,
    selectedDate: new Date().toISOString().split('T')[0], // 默认设置为当天日期
    selectedStatus: 'normal', // 默认设置为normal状态
    statusOptions: [
      {label: '全部', value: null},
      {label: '正常', value: 'normal'},
      {label: '已取消', value: 'canceled'},
      {label: '延误', value: 'delayed'}
    ]
  },

  // 新增日期选择处理
  onDateChange: function(e) {
    this.setData({
      selectedDate: e.detail.value,
      schedules: [],
      currentPage: 1,
      hasMore: true
    });
    this.loadSchedules();
  },

  // 新增状态选择处理
  onStatusChange: function(e) {
    const status = this.data.statusOptions[e.detail.value].value;
    this.setData({
      selectedStatus: status,
      schedules: [],
      currentPage: 1,
      hasMore: true
    });
    this.loadSchedules();
  },

  // 修改loadSchedules方法
  loadSchedules: function() {
    if (this.data.isLoading) return;
    
    this.setData({ isLoading: true });
    
    getDriverSchedules(this.data.selectedDate, this.data.selectedStatus)
      .then(data => {
        this.setData({
          schedules: data.schedules, // 直接赋值而不是concat
          isLoading: false
        });
      })
      .catch(() => {
        this.setData({ isLoading: false });
      });
  },
  
  // 下拉刷新
  onPullDownRefresh: function() {
    this.setData({
      schedules: [],
      currentPage: 1,
      hasMore: true
    });
    this.loadSchedules();
    wx.stopPullDownRefresh();
  },
  
  // 页面显示时加载数据
  onShow: function () {
    if (typeof this.getTabBar === 'function' &&  this.getTabBar()) {
    this.getTabBar().setData({
       selected: 1
      })
    };
    console.log('userInfo:', app.globalData.userInfo); // 添加调试日志
    this.loadSchedules();
  },
  

  // 新增导航到班次详情页的方法
  navigateToScheduleDetail: function(e) {
    const scheduleId = e.currentTarget.dataset.id // 获取班次ID
    wx.navigateTo({
      url: `/pages/driver/schedule-detail/schedule-detail?scheduleId=${scheduleId}` // 跳转并传递参数
    })
  }
});