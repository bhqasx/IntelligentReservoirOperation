function GenerateIniP(){
  //读取XLD_keypoints.json和SMX_keypoints.json中的数据
  var XLD_KeyP = JSON.parse(document.getElementById('XLD_keypoints').value);
  var SMX_KeyP = JSON.parse(document.getElementById('SMX_keypoints').value);
  //设置方案数量
  var planNum = 8;
  //设置最迟开始时间
  var t2_lim = 200;
}

// Make the function available globally
window.GenerateIniP = GenerateIniP;