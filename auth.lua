-- 简单的权限验证
-- by Sunmoon
local function forbidden()
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.say("{\"status\": 401, \"message\": \"Unauthorized\"}")
    return ngx.exit(ngx.HTTP_OK)
end
local upload_user = ngx.req.get_headers()["UPLOAD-SERVER-USER"]
local upload_token = ngx.req.get_headers()["UPLOAD-SERVER-TOKEN"]
local secretkey='k4Ao7KWVbvg3Z2L6KLwN9OoDjQL5SioJffIPoODATxCynuEVEAt0278kg7r9FHiS'
if upload_user == nil or upload_token == nil then
    return forbidden()
end

-- 当前时间 小时
local date = os.date("%Y%m%d%H");

local token = ngx.md5('uid:' .. tostring(upload_user) .. '&secretkey:' .. tostring(secretkey) .. '&datetime:' .. tostring(date))

if token ~= upload_token then
    return forbidden()
end