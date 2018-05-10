<?php
date_default_timezone_set('PRC');
$id='234';
$date = date('YmdH');
$authKey = 'k4Ao7KWVbvg3Z2L6KLwN9OoDjQL5SioJffIPoODATxCynuEVEAt0278kg7r9FHiS';
$hash = 'uid:'.(string)$id.'&secretkey:'.(string)$authKey.'&datetime:'.(string)$date;
echo md5($hash);