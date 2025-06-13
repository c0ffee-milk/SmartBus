Component({
  /**
   * 组件的属性列表
   * @property {boolean} show - 控制弹窗显示隐藏
   * @property {string} title - 弹窗标题
   */
  properties: {
    show: Boolean,
    title: String
  },

  /**
   * 组件的初始数据
   */
  data: {
    name: '',
    card: ''
  },

  /**
   * 组件的方法列表
   */
  methods: {
    /**
     * 阻止触摸穿透
     */
    preventTouchMove() {},

    /**
     * 隐藏弹窗
     */
    hideModal() {
      this.triggerEvent('hide');
    },

    /**
     * 处理姓名输入
     * @param {Object} e - 输入事件对象
     */
    onNameInput(e) {
      this.setData({
        name: e.detail.value
      });
    },

    /**
     * 处理学号输入
     * @param {Object} e - 输入事件对象
     */
    onCardInput(e) {
      this.setData({
        card: e.detail.value
      });
    },

    /**
     * 确认输入
     */
    confirm() {
      const { name, card } = this.data;
      this.triggerEvent('confirm', { name, card });
      this.hideModal();
    }
  }
});