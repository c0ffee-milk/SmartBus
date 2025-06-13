// 获取应用实例
const app = getApp()

Page({
  /**
   * 页面的初始数据
   */
  data: {
    schedule: null, // 班次详情
    passengers: [], // 乘客列表
    loading: true, // 加载状态
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    const { scheduleId } = options // 从路由参数获取班次ID
    this.getScheduleDetail(scheduleId) // 获取班次详情
    this.getPassengerList(scheduleId) // 获取乘客列表
  },

  /**
   * 获取班次详情
   */
  getScheduleDetail(scheduleId) {
    wx.request({
      url: app.globalData.baseUrl + '/drivers/schedules/' + scheduleId,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.accessToken,  
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ 
            schedule: res.data.schedule,
            loading: false
          })
        }
      },
      fail: (err) => {
        console.error('获取班次详情失败', err)
        wx.showToast({ title: '获取班次详情失败', icon: 'none' })
      }
    })
  },

  /**
   * 获取乘客列表
   */
  getPassengerList(scheduleId) {
    wx.request({
      url: app.globalData.baseUrl + '/drivers/schedules/' + scheduleId + '/passengers',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.accessToken,  
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({ passengers: res.data.passengers })
        }
      },
      fail: (err) => {
        console.error('获取乘客列表失败', err)
        wx.showToast({ title: '获取乘客列表失败', icon: 'none' })
      }
    })
  },

  /**
   * 刷新数据
   */
  onPullDownRefresh() {
    const { schedule } = this.data
    if (schedule) {
      this.getScheduleDetail(schedule.id)
      this.getPassengerList(schedule.id)
    }
    wx.stopPullDownRefresh()
  }
})