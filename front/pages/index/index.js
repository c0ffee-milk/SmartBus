// index.js
const app = getApp();
const baseUrl = app.globalData.baseUrl;
Page({

  onShow: function () {
    if (typeof this.getTabBar === 'function' &&  this.getTabBar()) {
      this.getTabBar().setData({
        selected: 0
      })
    };

    if (!app.globalData.accessToken) {
      wx.showModal({
        title : '未认证',
        content : '请先完成身份认证',
        confirmText : '去认证',
        success(res) {
          if(res.confirm) {
            wx.switchTab({
              url: '/pages/mines/mines'
            })
          }
        }
      })
    };

    if (this.data.startPoint && this.data.endPoint) {
      this.fetchSchedulesData();
    }
  },

  onPullDownRefresh() {
    this.fetchSchedulesData();
    wx.stopPullDownRefresh();
  },

  data: {
    startPoint: '武大本部网安院',
    endPoint: '新校区新珈楼门口',
    schedules: [],
    selectedDate: new Date().toLocaleDateString('zh-CN', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit' 
    }).replace(/\//g, '-') // 格式化为YYYY-MM-DD
  },

  // 获取班次数据
  fetchSchedulesData: function () {
    const baseUrl = app.globalData.baseUrl;
    const {startPoint , endPoint, selectedDate} = this.data;
    wx.request({
      url: `${baseUrl}/reservations/available-schedules`,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.accessToken,  
        'Content-Type': 'application/json'
      },
      data: {
        start_point: startPoint,
        end_point: endPoint,
        date: selectedDate 
      },
      success: (res) => {
        if (res.statusCode === 200) {
          this.setData({
            schedules: res.data.schedules
          });
          console.log(res.data.schedules);
          wx.showToast({
            title : "获取数据成功",
            icon : 'success'
          })
        } else {
          wx.showToast({
            title: res.data.error || '获取班次信息失败',
            icon: 'none'
          });
        }
      },
      fail: () => {
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    })
  },

  // 处理班次预约/取消预约
  handleSchedule: function(event) {
    const id = event.currentTarget.id;  // 获取班次id
    const schedule = this.data.schedules.find(item => item.id === id); 

    if (schedule.is_booked) {
      // 取消预约
      wx.request({
        url: `${baseUrl}/reservations/cancel`,
        method: 'POST',
        header: {
          'Authorization': 'Bearer ' + app.globalData.accessToken,
          'Content-Type': 'application/json'
        },
        data: {
          schedule_id: schedule.id
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data.message) {
            wx.showToast({
              title: '取消预约成功',
              icon: 'success'
            });
            // 立即更新本地数据状态
            const schedules = this.data.schedules.map(item => {
              if (item.id === schedule.id) {
                return {...item, is_booked: false};
              }
              return item;
            });
            this.setData({ schedules });
            this.fetchSchedulesData(); // 仍然保留API调用确保数据同步
          } else {
            wx.showToast({
              title: res.data.error || '取消预约失败',
              icon: 'none'
            });
          }
        },
        fail: () => {
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          });
        }
      });
    } else {
      // 预约成功后的处理
      wx.request({
        url: `${baseUrl}/reservations/create`,
        method: 'POST',
        header: {
          'Authorization': 'Bearer ' + app.globalData.accessToken,
          'Content-Type': 'application/json'
        },
        data: {
          schedule_id: schedule.id
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data.reservation) {  // 检查reservation字段
            wx.showToast({
              title: '预约成功',
              icon: 'success'
            });
            this.fetchSchedulesData(); // 新增：预约成功后刷新数据
          } else {
            wx.showToast({
              title: res.data.error || '预约失败',
              icon: 'none'
            });
          }
        },
        fail: () => {
          wx.showToast({
            title: '网络错误',
            icon: 'none'
          });
        }
      });
    }
  },

  // 选择起点
  selectStartPoint() {
    const locations = ['武大本部网安院', '武大本部当代楼附近校巴站', '新校区新珈楼', '新校区一食堂'];
    wx.showActionSheet({
      itemList: locations,
      success: (res) => {
        this.setData({
          startPoint: locations[res.tapIndex],
        });
        this.fetchSchedulesData();
      },
      fail: (res) => {
        console.error(res.errMsg);
      }
    });
  },

  // 选择终点
  selectEndPoint() {
    const { startPoint } = this.data;
    let locations = [];
    if (startPoint.includes('本部')) {
      locations = ['新校区新珈楼门口', '新校区一食堂门口'];
    } else {
      locations = ['武大本部网安院', '武大本部当代楼附近校巴站']; 
    }
    wx.showActionSheet({
      itemList: locations,
      success: (res) => {
        this.setData({
          endPoint: locations[res.tapIndex]
        },() => {
          this.fetchSchedulesData();
        });
      },
      fail: (res) => {
        console.error(res.errMsg);
      }
    });
  },

  // 选择日期
  selectDate() {
    const dates = ['今天', '明天'];
    wx.showActionSheet({
      itemList: dates,
      success: (res) => {
        const today = new Date();
        let selectedDate;
        if (dates[res.tapIndex] === '今天') {
          selectedDate = today.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
          }).replace(/\//g, '-');
        } else {
          const tomorrow = new Date(today);
          tomorrow.setDate(tomorrow.getDate() + 1);
          selectedDate = tomorrow.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
          }).replace(/\//g, '-');
        }
        this.setData({
          selectedDate: selectedDate
        }, () => {
          this.fetchSchedulesData();
        });
      },
      fail: (res) => {
        console.error(res.errMsg);
      }
    });
  },
});