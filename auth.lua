-- 简单的权限验证
-- by Sunmoon
local function forbidden()
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header.content_type = "application/json; charset=utf-8"
    ngx.say("{\"status\": 401, \"message\": \"Unauthorized\", \"error\": 1}")
    return ngx.exit(ngx.HTTP_OK)
end
local function simple_debug(msg)
    ngx.say(msg)
    return ngx.exit(ngx.HTTP_OK)
end
local function set_logger(msg)
    local cur_time = os.date('%Y-%m-%d %H:%M:%S');
    local log_name = os.date("%Y%m%d%H") .. "_auth_lua.log"
    local log_file = cc.FileUtils:getInstance():getWritablePath() .. "logs/" .. log_name
    io.writefile(log_file, '[' .. cur_time .. ']' .. msg .. "\n", "a+")
end
local upload_user = ngx.req.get_headers()["UPLOAD-SERVER-USER"]
local upload_token = ngx.req.get_headers()["UPLOAD-SERVER-TOKEN"]
local upload_date = ngx.req.get_headers()["UPLOAD-SERVER-DATE"]
local upload_notify_url = ngx.req.get_headers()["UPLOAD-SERVER-NOTIFY-URL"]
local secretkey='k4Ao7KWVbvg3Z2L6KLwN9OoDjQL5SioJffIPoODATxCynuEVEAt0278kg7r9FHiS'
if upload_user == nil or upload_token == nil then
    local log_msg = '[USER]' .. upload_user .. '[TOKEN]' .. upload_token .. '[DATE]' .. upload_date .. '[NOTIFY-URL]' .. upload_notify_url
    set_logger(log_msg)
    return forbidden()
end

local date = os.date("%Y%m%d%H")
if upload_date == nil then
    upload_date = date
end
local string = 'uid:' .. tostring(upload_user) .. '&secretkey:' .. tostring(secretkey) .. '&datetime:' .. tostring(upload_date) .. '&notifyurl:' .. tostring(upload_notify_url)
local token = ngx.md5(string)

if token ~= upload_token then
    local log_msg_error = '[USER]' .. upload_user .. '[TOKEN]' .. upload_token .. '[AUTH_LUA_TOKEN]' .. token .. '[DATE]' .. upload_date .. '[NOTIFY-URL]' .. upload_notify_url
    set_logger(log_msg_error)
    return forbidden()
end