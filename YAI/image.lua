--Writes image to display using output from python script
--@author schnwil

local component = require("component")
local gpu = component.gpu
local unicode = require("unicode")
local fs = require("filesystem")

local image = {}

--checks and constants
local hres = 32
local lres = 16
local sig = {89, 65, 73, 76}
local version = 1

--quantization information
local rv = {0, 51, 102, 153, 204, 255}
local gv = {0, 36, 73, 109, 146, 182, 216, 255}
local bv = {0, 64, 128, 192, 255}

--Get the current backround and foreground colors.
--@return number, number: bgColor, fgColor
function image.getColors()
  local bgColor, tmp = gpu.getBackground()
  if tmp then
    bgColor = gpu.getPaletteColor(bgColor)
  end
  
  local fgColor, tmp = gpu.getForeground()
  if tmp then
    fgColor = gpu.getPaletteColor(fgColor)
  end
  return bgColor, fgColor
end

--Reset the entire screen. If color is nil uses current color palette
--@param bgColor (number): background color
function image.reset(bgColor)
  local xMax, yMax = gpu.maxResolution()
  image.fillRect(1, 1, xMax, yMax, bgColor)
end

--Set rectangle bounded by params with passed in color
--@param x,y (number, number): top left corner
--@param xOff, yOff (number, number): bottom right corner
--@param bgColor (number): color value. Uses current bgColor if nil
function image.fillRect(x, y, xOff, yOff, bgColor)
  local bgColorPrev = image.getColors()

  if bgColor == nil then
    bgColor = bgColorPrev
  end

  gpu.setBackground(bgColor)
  gpu.fill(x, y, xOff, yOff, " ")
  gpu.setBackground(bgColorPrev)
end

--Display image on screen
--@param filepath (string): absolute file path to image
--@param xOff, yOff (number, number): start offset from top left
--@param timer (boolean): true returns time in seconds
function image.imshow(filepath, xOff, yOff, timer)
  return image.imshowCrop(filepath, xOff, yOff, 160-xOff, 50-yOff, timer)
end

--Display image on screen with cropping
--@param filepath (string): absolute file path to image
--@param xOff, yOff (number, number): start offset from top left
--@param xCut, yCut (number, number): max number of units in each dimension from top left
--@param timer (boolean): true returns time in seconds
function image.imshowCrop(filepath, xOff, yOff, xCut, yCut, timer)
  --asserts and nil checks
  assert(type(filepath) == "string", "filepath must be a string of the absolute file path")
  if xOff == nil then xOff = 0 end
  if yOff == nil then yOff = 0 end
  if timer == nil then timer = false end

  local fp = filepath

  if fs.exists(fp) == false then
    io.stderr:write("Error - file does not exist, filepath must be the absolute path\n")
    return
  end

  local f = io.open(fp, "rb")
  
  --check header and size
  local header = {0, 0, 0, 0}
  
  for i=1,4,1 do
    header[i] = f:read(1):byte()

    if header[i] ~= sig[i] then
      io.stderr:write("Error - wrong header\n")
      return
    end
  end
  
  local vers = f:read(1):byte()
  if vers ~= version then
    io.stderr:write(string.format("Error - wrong version: File=%i, YAI=%i\n", vers, version))
    return
  end
  
  local fb = f:read(1):byte()
  if fb == hres then return image._showHRes(f, xOff, yOff, xCut, yCut, timer)
  elseif fb == lres then return image. _showLRes(f, xOff, yOff, xCut, yCut, timer)
  else io.stderr:write("Error - unknown resolution byte\n") end
  
  f:close()
  
end

--Convert byte containing RGB information in three integers
--If the byte is over 239 then the color comes from the custom palette
--@param colorByte (number): a value of 0~255 representing 6-8-5 RGB color
--@return r,b,g (number, number, number): channel value 0~255
function image._byte2RGB(colorByte)
  if colorByte >= 240 then
    local color = gpu.getPaletteColor(colorByte - 240)
    local r = math.floor(color / 65536)
    local g = math.floor((color % 65536) / 256)
    local b = math.floor(color % 256)
    return r, g, b
  end

  local r = math.floor(colorByte / 40) + 1
  local g = math.floor((colorByte % 40) / 5) + 1
  local b = math.floor(colorByte % 5) + 1
  return rv[r], gv[g], bv[b]
end

--Write low resolution image to display
--@param f (file): open file at position 7th byte
--@param xOff, yOff (number, number): start offset from top left
--@param xCut, yCut (number, number): max number of units in each dimension from top left
--@param timer (boolean): true returns time in seconds for imshow
function image._showLRes(f, xOff, yOff, xCut, yCut, timer)
  local start = os.time()
  local xSize, ySize
  local xMax, yMax = gpu.maxResolution()

  xCut = xCut + xOff
  yCut = yCut + yOff
  xSize = f:read(1):byte()
  ySize = f:read(1):byte()

  if xSize > xMax or ySize > yMax then
    io.stderr:write(string.format("Error - wrong size (x,y): %i %i\n", xSize, ySize))
    return
  end
  
  local paletteLen = f:read(1):byte()
  
  for i=0,paletteLen-1,1 do
    local color = "0x"
    for j=1,3,1 do
      color = color .. string.format("%02x", f:read(1):byte())
    end
    gpu.setPaletteColor(i, tonumber(color))
  end
  
  --get current colors
  local bgColorCur, fgColorCur = image.getColors()
  
  --main variables
  local bgColor, bgColorPrev
  local fgColor, fgColorPrev
  local chunknum = 1
  local fb
  
  --main loop
  while chunknum < xSize*ySize do
    --get bgColor
    bgColor = "0x"
    fb = f:read(1):byte()
    local r,g,b = image._byte2RGB(fb)
    bgColor = "0x" .. string.format("%02x%02x%02x", r, g ,b)

    --don't change bgColor if it hasn't changed
    if bgColor ~= bgColorPrev then
      bgColorPrev = bgColor
      gpu.setBackground(tonumber(bgColor))
    end

    --get fgColor
    fgColor = "0x"
    fb = f:read(1):byte()
    local r,g,b = image._byte2RGB(fb)
    fgColor = "0x" .. string.format("%02x%02x%02x", r, g ,b)

    --don't change fgColor if it hasn't changed
    if fgColor ~= fgColorPrev then
      fgColorPrev = fgColor
      gpu.setForeground(tonumber(fgColor))
    end

    fb = f:read(1):byte()

    --table entry loop, get coordinates and paint pixel
    while(fb ~= 255) do
      local x = fb + xOff
      local y = f:read(1):byte() + yOff

      if x > xCut or y > yCut then goto continue end
      
      gpu.set(x, y, unicode.char(0x2584))
      
      ::continue::
      
      fb = f:read(1):byte()
      chunknum = chunknum + 1
    end

  end

  gpu.setBackground(bgColorCur)
  gpu.setForeground(fgColorCur)

  if timer then
    return (os.time()-start)/72
  end
end

--Write high resolution image to display
--@param f (file): open file at position 7th byte
--@param xOff, yOff (number, number): start offset from top left
--@param xCut, yCut (number, number): max number of units in each dimension from top left
--@param timer (boolean): true returns time in seconds for imshow
function image._showHRes(f, xOff, yOff, xCut, yCut, timer)
  local start = os.time()
  local xSize, ySize
  local xMax, yMax = gpu.maxResolution()

  xCut = xCut + xOff
  yCut = yCut + yOff
  xSize = f:read(1):byte()
  ySize = f:read(1):byte()
  local paletteLen = f:read(1):byte()
  
  for i=0,paletteLen-1,1 do
    local color = "0x"
    for j=1,3,1 do
      color = color .. string.format("%02x", f:read(1):byte())
    end
    gpu.setPaletteColor(i, tonumber(color))
  end

  if xSize > xMax or ySize > yMax then
    io.stderr:write(string.format("Error - wrong size (x,y): %i %i\n", xSize, ySize))
    return
  end
  
  --get current colors
  local bgColorCur, fgColorCur = image.getColors()
  
  --main variables
  local bgColor, bgColorPrev
  local fgColor, fgColorPrev
  local symbol
  local chunknum = 1
  local fb

  --main loop
  while chunknum < xSize*ySize do

    fb = f:read(1):byte()
    symbol = fb

    --get bgColor
    fb = f:read(1):byte()
    local r,g,b = image._byte2RGB(fb)
    bgColor = "0x" .. string.format("%02x%02x%02x", r, g ,b)

    --don't change bgColor if it hasn't changed
    if bgColor ~= bgColorPrev then
      bgColorPrev = bgColor
      gpu.setBackground(tonumber(bgColor))
    end

    --not fill check
    if symbol ~= 0 then
      fgColor = "0x"

      --get fgColor
      fb = f:read(1):byte()
      local r,g,b = image._byte2RGB(fb)
      fgColor = "0x" .. string.format("%02x%02x%02x", r, g ,b)

      --don't change fgColor if it hasn't changed
      if fgColor ~= fgColorPrev then
        fgColorPrev = fgColor
        gpu.setForeground(tonumber(fgColor))
      end

    end

    fb = f:read(1):byte()

    --table entry loop, get coordinates and paint pixel
    while(fb ~= 255) do
      local x = fb + xOff
      local y = f:read(1):byte() + yOff
      
      if x > xCut or y > yCut then goto continue end

      gpu.set(x, y, unicode.char(0x2800 + symbol))
      
      ::continue::
      
      fb = f:read(1):byte()
      chunknum = chunknum + 1
    end

  end

  gpu.setBackground(bgColorCur)
  gpu.setForeground(fgColorCur)

  if timer then
    return (os.time()-start)/72
  end
end

return image