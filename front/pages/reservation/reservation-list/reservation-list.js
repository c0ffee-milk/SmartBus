const app = getApp();
const baseUrl = app.globalData.baseUrl; 

Page({
  onShow: function () {
    if (typeof this.getTabBar === 'function' &&  this.getTabBar()) {
      this.getTabBar().setData({
        selected: 1
      })
    }
    // 调用获取预约列表的函数
    this.getReservationList();
  },

  data: {
    isLoading: true, // 请求数据时显示加载中
    reservationList: [],
    status: null,
    statusList: ['null', 'active', 'checked_in', 'canceled', 'absent'], // 后端状态值
    statusDisplayList: ['全部状态', '待完成', '已完成', '已取消', '违约'], // 前端显示的中文状态
    selectedStatusIndex: -1,
  },

  bindStatusChange: function(e) {
    const index = e.detail.value;
    const status = this.data.statusList[index]; // 使用英文状态值
    this.setData({
      selectedStatusIndex: index,
      status: status
    });
    // 重新获取预约列表
    this.getReservationList();
  },

  getReservationList: function() {
    const that = this;
    // 设置加载状态为 true
    that.setData({
      isLoading: true
    });

    wx.request({
      url: `${baseUrl}/reservations/list`, 
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.accessToken,
        'Content-Type': 'application/json'
      },
      data : {
        status : this.data.status, 
      },
      success: function(res) {
        if (res.statusCode === 200) {
          // 请求成功，处理返回的reservations数组
          const reservations = res.data.reservations || [];
          // 格式化数据供前端显示
          // 状态映射关系
          const statusMap = {
            'active': '待完成',
            'checked_in': '已完成',
            'canceled': '已取消',
            'absent': '违约'
          };
          
          // 在格式化数据时使用映射
          const formattedList = reservations.map(item => ({
            id: item.id,
            scheduleId: item.schedule_id.replace(/[a-zA-Z]/g, ''), 
            seatNumber: item.seat_number,
            status: statusMap[item.status] || item.status,
            reservationTime: item.reserved_at ? new Date(item.reserved_at).toLocaleString() : '未知时间',
            canceledTime: item.canceled_at ? new Date(item.canceled_at).toLocaleString() : null,
            isTeacherPriority: item.priority_used,
            qrCode: item.qr_code,
            // 添加原始时间戳用于排序
            timestamp: item.reserved_at ? new Date(item.reserved_at).getTime() : 0
          }));
          
          // 按时间戳降序排序
          formattedList.sort((a, b) => b.timestamp - a.timestamp);
          
          that.setData({
            reservationList: formattedList,
            isLoading: false
          });
        } else {
          // 请求失败，给出提示
          wx.showToast({
            title: '获取预约列表失败',
            icon: 'none'
          });
          that.setData({
            isLoading: false
          });
        }
      },
      fail: function(err) {
        // 请求出错，给出提示
        wx.showToast({
          title: '网络请求出错',
          icon: 'none'
        });
        that.setData({
          isLoading: false
        });
      }
    });
  },

  // 新增：处理取消预约
  handleCancelReservation: function(e) {
    const scheduleId = e.currentTarget.dataset.scheduleId;
    const that = this;

    // 显示确认对话框
    wx.showModal({
      title: '确认取消',
      content: '确定要取消该预约吗？',
      success: function(res) {
        if (res.confirm) {
          // 用户点击确定，发送取消请求
          wx.request({
            url: `${baseUrl}/reservations/cancel`,
            method: 'POST',
            header: {
              'Authorization': 'Bearer ' + app.globalData.accessToken,
              'Content-Type': 'application/json'
            },
            data: {
              schedule_id: scheduleId
            },
            success: (res) => {
              if (res.statusCode === 200 && res.data.message) {
                wx.showToast({
                  title: '取消预约成功',
                  icon: 'success'
                });
                // 刷新预约列表
                that.getReservationList();
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
        }
      }
    });
  },

  handleModalButtonTap(e) {
    const id = e.currentTarget.dataset.id;
    wx.showLoading({
      title: '加载中...',
      mask: true
    });
    
    // 添加500ms延迟确保loading显示
    setTimeout(() => {
      wx.navigateTo({
        url: `/pages/reservation/reservation-details/reservation-details?id=${id}`,
        complete: () => {
          wx.hideLoading(); // 页面跳转完成后隐藏loading
        }
      });
    }, 500);
  }
})
