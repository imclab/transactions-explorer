customMatchers = {
  shouldContain: function( list ) {
    var okay = true;
    for (var i = 0; i < list.length; i++) {
      console.log(this,this.actual.toString());
      if(this.actual.toString().indexOf(list[i]) == -1){
        okay = false;
        break;
      }
    }
    return okay;
  }
}
