// pages/admin/orders/orders.js
const app = getApp();  
const baseUrl = app.globalData.baseUrl;  

Page({

    onShow: function () {
        if (typeof this.getTabBar === 'function' &&  this.getTabBar()) {
          this.getTabBar().setData({
            selected: 0
          })
        };
      },
    onLoad(options) {
          this.loadSchedules(); 
      },

    data: {
        currentDate: new Date().toISOString().split('T')[0],  
        schedules: [],  
        showDialog: false,  
        currentSchedule: null, 

        dialogType: '',  
        directionOptions: [
            {id: 'A', name: 'A方向(本部→新校区)'},
            {id: 'B', name: 'B方向(新校区→本部)'}
        ],
        directionIndex: 0,
        startPointOptions: ['武大本部网安院', '武大本部当代楼附近校巴站', '新校区新珈楼', '新校区一食堂'],
        startPointIndex: 0,
        endPointOptions: ['新校区新珈楼门口', '新校区一食堂门口', '武大本部网安院', '武大本部当代楼附近校巴站'],
        endPointIndex: 0,
        
        formData: {
            direction: 'A',
            start_point: '武大本部网安院',
            end_point: '新校区新珈楼门口',
            departure_datetime: '',
            dynamic_capacity: '',
            vehicle_plate: '',
            driver_id: '',
            status: 'normal'
        },

        selectDate : '',
        selectTime : ''
        
    },

    onDateChange: function(e) {
        this.setData({ 
            currentDate: e.detail.value,
            schedules: [] // 清空列表等待加载新数据
        });
        this.loadSchedules();
    },

    loadSchedules: function() {
        const that = this;
        wx.request({
            url: `${baseUrl}/admin/schedules`,
            method: 'GET',
            header: {
                'Authorization': 'Bearer ' + app.globalData.accessToken,
                'Content-Type': 'application/json'
            },
            data: {
                date: this.data.currentDate
            },
            success(res) {
                if (res.statusCode === 200 && res.data && res.data.schedules) {
                    const schedules = res.data.schedules.map(item => ({
                        id: item.id,
                        time: item.departure_time.split(' ')[1],
                        route: item.route_name,
                        start: item.start_point,
                        end: item.end_point,
                        seats: item.capacity,
                        reserved: item.reserved_count,
                        plate: item.vehicle_plate,
                        driver: item.driver_name,
                        status: item.status
                    }));
                    that.setData({ schedules });
                } else {
                    wx.showToast({
                        title: res.data.error || '获取班次失败',
                        icon: 'none'
                    });
                    that.setData({ schedules: [] });
                }
            },
            fail() {
                wx.showToast({
                    title: '网络错误',
                    icon: 'none'
                });
            }
        });
    },

    selectStartPoint: function() {
        const isDirectionA = this.data.directionOptions[this.data.directionIndex].id === 'A';
        const locations = isDirectionA 
            ? ['武大本部网安院', '武大本部当代楼附近校巴站']  // A方向起点选项
            : ['新校区新珈楼', '新校区一食堂'];  // B方向起点选项
        wx.showActionSheet({
            itemList: locations,
            success: (res) => {
                this.setData({
                    startPointIndex: res.tapIndex,
                    'formData.start_point': locations[res.tapIndex],
                    endPointIndex: 0,
                    'formData.end_point': this.data.endPointOptions[0]
                });
            },
            fail: (res) => {
                console.error(res.errMsg);
            }
        });
    },

    selectEndPoint: function() {
        const isDirectionA = this.data.directionOptions[this.data.directionIndex].id === 'A';
        const locations = isDirectionA 
            ? ['新校区新珈楼门口', '新校区一食堂门口']  
            : ['武大本部网安院', '武大本部当代楼附近校巴站'];  
        wx.showActionSheet({
            itemList: locations,
            success: (res) => {
                this.setData({
                    endPointIndex: res.tapIndex,
                    'formData.end_point': locations[res.tapIndex]
                });
            },
            fail: (res) => {
                console.error(res.errMsg);
            }
        });
    },

    onDirectionChange: function(e) {
        const selectedId = this.data.directionOptions[e.detail.value].id;  // 获取选中项的id值
        const isDirectionA = selectedId === 'A';  // 判断是否为A方向
        
        // 根据方向设置起点和终点选项
        const startPoints = isDirectionA 
            ? ['武大本部网安院', '武大本部当代楼附近校巴站']  // A方向起点选项
            : ['新校区新珈楼', '新校区一食堂'];  // B方向起点选项
            
        const endPoints = isDirectionA 
            ? ['新校区新珈楼门口', '新校区一食堂门口']  // A方向终点选项
            : ['武大本部网安院', '武大本部当代楼附近校巴站'];  // B方向终点选项

        this.setData({
            directionIndex: e.detail.value,
            startPointOptions: startPoints,  // 更新起点选项
            endPointOptions: endPoints,     // 更新终点选项
            startPointIndex: 0,             // 设置为第一个选项
            endPointIndex: 0,               // 设置为第一个选项
            'formData.direction': selectedId,
            'formData.start_point': startPoints[0],  // 自动选择第一个起点
            'formData.end_point': endPoints[0]      // 自动选择第一个终点
        });
    },

    onSelectDateChange: function(e) {
        this.setData({
            selectDate: e.detail.value,
        });
    },

    onSelectTimeChange: function(e) {
        this.setData({
            selectTime: e.detail.value,
        });
    },
    
    addSchedule: function() {
        this.setData({
            showDialog: true,
            dialogType: 'add',
            formData: {  // 初始化formData对象
                direction: 'A',
                start_point: '武大本部网安院',
                end_point: '新校区新珈楼门口',
                departure_datetime: '',  
                vehicle_plate: '',
                driver_id: '',
                dynamic_capacity: 30,
                status: 'normal'
            }
        });
    },

    deleteSchedule: function(e) {
        const id = e.currentTarget.dataset.id;
        const that = this;
        wx.showModal({
            title: '确认删除',
            content: '确定要删除这个班次吗？',
            success: (res) => {
                if (res.confirm) {
                    wx.request({
                        url: `${baseUrl}/admin/schedules/${id}`,
                        method: 'DELETE',
                        header: {
                            'Authorization': 'Bearer ' + app.globalData.accessToken,
                            'Content-Type': 'application/json'
                        },
                        success(res) {
                            if (res.statusCode === 200) {
                                wx.showToast({
                                    title: '删除成功',
                                    icon: 'success'
                                });
                                that.loadSchedules(); // 刷新列表
                            } else {
                                wx.showToast({
                                    title: res.data.error || '删除失败',
                                    icon: 'none'
                                });
                            }
                        },
                        fail() {
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

    editSchedule: function(e) {
        const id = e.currentTarget.dataset.id;
        const schedule = this.data.schedules.find(item => item.id === id);
        if (!schedule) {  // 检查班次是否存在
            wx.showToast({title: '班次数据异常', icon: 'none'});
            return;
        }
        
        // 处理时间格式（后端返回的是单独的时间字段）
        const time = schedule.time || '00:00';  // 默认值处理
        const date = this.data.currentDate;  // 使用当前日期
        
        this.setData({
            showDialog: true,
            dialogType: 'edit',
            currentSchedule: schedule,
            selectDate: date,  // 设置日期
            selectTime: time,  // 设置时间
            formData: {  // 初始化表单数据
                direction: schedule.route.includes('本部→新校区') ? 'A' : 'B',  // 根据路线判断方向
                departure_datetime: `${date} ${time}`,  
                dynamic_capacity: schedule.seats || '',  
                vehicle_plate: schedule.plate || '',  
                driver_id: '',  // 司机ID为空
                status: schedule.status || 'normal',
                start_point: schedule.start || '武大本部网安院',
                end_point: schedule.end || '新校区新珈楼门口'
            }
        });
    },

    closeDialog: function() {
        this.setData({
            showDialog: false,
            dialogType: '',
            currentSchedule: null
        });
    },

    submitForm: function() {
        const formData = this.data.formData;
        console.log(formData)
        if (!formData.start_point || !formData.end_point || !formData.dynamic_capacity) {
            wx.showToast({title: '请填写所有必填字段', icon: 'none'});
            return;
        }
        const that = this;
        const departure_datetime = `${this.data.selectDate} ${this.data.selectTime}`;

        const url = this.data.dialogType === 'add' 
            ? `${baseUrl}/admin/schedules`
            : `${baseUrl}/admin/schedules/${this.data.currentSchedule.id}`;
        const method = this.data.dialogType === 'add' ? 'POST' : 'PUT';
        
        const requestData = {
            direction: formData.direction,

            departure_datetime: departure_datetime,
            dynamic_capacity: formData.dynamic_capacity,
            start_point: formData.start_point, 
            end_point: formData.end_point,

            status: formData.status || 'normal', 

            driver_id: formData.driver_id,
            vehicle_plate: formData.vehicle_plate
        };

        console.log(requestData);

        wx.request({
            url: url,
            method: method,
            header: {
                'Authorization': 'Bearer ' + app.globalData.accessToken,
                'Content-Type': 'application/json'
            },
            data: requestData,
            success(res) {
                if (res.statusCode === 200) {
                    wx.showToast({
                        title: '操作成功',
                        icon: 'success'
                    });
                    that.closeDialog();
                    that.loadSchedules();
                } else {
                    wx.showToast({
                        title: res.data.error || '操作失败',
                        icon: 'none'
                    });
                }
            },
            fail() {
                wx.showToast({
                    title: '网络错误',
                    icon: 'none'
                });
            }
        });
    },

    handleDynamicCapacityInput: function(e) {
        this.setData({
            'formData.dynamic_capacity': e.detail.value  // 直接更新座位数
        });
    },
})
