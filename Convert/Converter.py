'''
Created on Jul 14, 2017
Converts images to data format for displaying with image.lua

@author: schnwil
'''
from PIL import Image
from imageConverter import Dither
import urllib.request, urllib.parse, sys, math

rv = [0, 51, 102, 153, 204, 255]
gv = [0, 36, 73, 109, 146, 182, 216, 255]
bv = [0, 64, 128, 192, 255]

def _get_quantized_colors():
    result = []
    for r in rv:
        for g in gv:
            for b in bv:
                result.append((r, g, b))
    
    return result

#constants
sig = [89, 65, 73, 76]
vers = 1
hres = 32
lres = 16
customPalette = {}
quantizedColors = _get_quantized_colors()

#Returns the RGB value at location and updates chunk
def _getPix(pix, x, y, chunk, mode='RGB'):
    if mode == 'RGB':
        s = str(pix[x, y]).replace(',', '')[1:-1]
        tokens = s.split()
        chunk.append([int(tokens[0]), int(tokens[1]), int(tokens[2])])
    elif mode == 'G':
        s = pix[x,y]
        chunk.append([int(s)])
    else:
        print('Error - unknown mode for get pixel data\n', file=sys.stderr)
    return

def _getColor(chunk, i):
    return (chunk[i][0], chunk[i][1], chunk[i][2])

def _padHex(hexStr):
    if len(hexStr) % 2:
        hexStr = '0' + hexStr
    return hexStr

def _vec2hex(colorVec):
    result = ''
    for i in range(3):
        h = hex(colorVec[i])[2:]
        result = result + _padHex(h)
    return result

def _getColorDist(color1, color2):
    return math.sqrt(math.pow((color2[0]-color1[0]), 2) + math.pow((color2[1]-color1[1]), 2) + math.pow((color2[2]-color1[2]), 2))

def _updatePalette():
    if len(customPalette) <= 16: return None, None
    
    eMin = 10000000
    replaceColor = ()
    replacedColors = {}
    black = (255,255,255)
    white = (0,0,0)
    
    if black in customPalette: 
        customPalette.pop(black)
        replacedColors[black] = black
    if white in customPalette:
        customPalette.pop(white)
        replacedColors[white] = white
    
    while len(customPalette) > 16:
        for color1 in customPalette:
            e = customPalette[color1]
            if e < eMin:
                eMin = e
                replaceColor = color1
                    
        customPalette.pop(replaceColor)
        replacedColors[replaceColor] = replaceColor
        eMin = 10000000
    
    quantizedReplacements = {}
    customReplacements = {}    
    for color in replacedColors:
        e1 = 10000000
        
        for color1 in customPalette:
            e2 = _getColorDist(color1, color)
            if e2 < e1:
                e1 = e2
                customReplacements[color] = color1
        for color1 in quantizedColors:
            e2 = _getColorDist(color1, color)
            if e2 < e1:
                quantizedReplacements[color] = color1   
    return customReplacements, quantizedReplacements

def _repaintPix(pix, x_size, y_size):
    customReplace, quantizedReplace = _updatePalette()
    
    for x in range(x_size):
        for y in range(y_size):
            color = pix[x,y]
            newColor = color
            colorFound = False
            
            for color2 in customPalette:
                if color2 == color:
                    colorFound = True
                    break
            if not colorFound:
                if color in customReplace:
                    newColor = customReplace[color]
                elif color in quantizedReplace:
                    newColor = quantizedReplace[color]
                pix[x,y] = newColor
    
    return pix

def _color2palette(color):
    quantColor = quantizedColor(color)
    quantizedColors.add(quantColor)
    if color in customPalette:
        customPalette[color] = customPalette[color] + 1
    else:
        customPalette[color] = 0
    return

def _color2byte2hex(color, customIdx):
    if color in quantizedColors:
        return _padHex(hex(rv.index(color[0])*40 + gv.index(color[1])*5 + bv.index(color[2]))[2:])
    else:
        return _padHex(hex(customIdx.index(color)+240)[2:])

def _getMixedData(chunk):
    result = ''
    chunkSize = len(chunk)
    color1 = _getColor(chunk, 0)
    color2 = color1
    
    for i in range(1,chunkSize):
        color2 = _getColor(chunk, i)
        if color2 != color1: break
    
    pix = [0,0,0,0,0,0,0,0]
    
    for i in range(chunkSize):
        tmpColor = _getColor(chunk, i)
        if tmpColor != color1:
            pix[i] = 1
    
    symbol = pix[0] + pix[1]*8 + pix[2]*2 + pix[3]*16 + pix[4]*4 + pix[5]*32 + pix[6]*64 + pix[7]*128
    
    customIdx = []
    for color in customPalette:
        customIdx.append(color)
    
    if chunkSize != 2:
        result = result + _padHex(hex(symbol)[2:])
    
    result = result + _color2byte2hex(color1, customIdx)

    if symbol != 0 or chunkSize == 2:
        result = result + _color2byte2hex(color2, customIdx)

    return result

#Returns symbol, background color, foreground color as string in hex
def _updateChunkAndPalette(chunk, ref=4):
    chunkSize = len(chunk)
    
    color1 = _getColor(chunk, ref)
    color2 = color1
    
    e = 0
    for i in range(0,chunkSize,1):
        if i == ref: continue
        tmpColor = _getColor(chunk, i)
        e1 = _getColorDist(color1, tmpColor)
        if e < e1:
            e = e1
            color2 = tmpColor
    
    _color2palette(color1)
    _color2palette(color2)
    
    #merge colors and find symbol
    for i in range(0,chunkSize,1):
        tmpColor = _getColor(chunk, i)
        e1 = _getColorDist(color1, tmpColor)
        e2 = _getColorDist(color2, tmpColor)
        if e1 > e2:
            chunk[i][0] = color2[0]
            chunk[i][1] = color2[1]
            chunk[i][2] = color2[2]
        else:
            chunk[i][0] = color1[0]
            chunk[i][1] = color1[1]
            chunk[i][2] = color1[2]
    return

#concats inputs
def _tabKey(symbol, bgColor, fgColor=''):
    return symbol + bgColor + fgColor

#Calls appropriate method for table creation
def _tabularizeData(data, res, xWidth):
    if res == 32:
        return _tabularizeDataHR(data, xWidth)
    elif res == 16:
        return _tabularizeDataLR(data, xWidth)
    else:
        print('Error - unknown resolution when tabularizing data\n', file=sys.stderr)

def _tabularizeDataLR(data, xWidth):
    pix = {}
    
    i = 0
    chunknum = 0
    curKey = ''
    
    while i < len(data):
        chunknum = chunknum + 1
        bgColor = ''
        fgColor = ''
        cords = [_padHex(hex(chunknum%xWidth)[2:]), _padHex(hex(int(chunknum/xWidth)+1)[2:])]
        
        if cords[0] == '00':
            cords[0] = _padHex(hex(xWidth)[2:])
            cords[1] = _padHex(hex(int(chunknum/xWidth))[2:])
        
        bgColor = data[i:i+2]
        fgColor = data[i+2:i+4]
        curKey = _tabKey('', bgColor, fgColor)
            
        if pix.get(curKey) == None:
            pix[curKey] = [cords]
        else:
            pix[curKey].append(cords)
        
        i = i + 4
            
    return pix
    
def _tabularizeDataHR(data, xWidth):
    pix = {}
    
    i = 0
    chunknum = 0
    prevKey = ''
    curKey = ''
    
    while i < len(data):
        chunknum = chunknum + 1
        symbol = data[i:i+2]
        bgColor = ''
        fgColor = ''
        cords = [_padHex(hex(chunknum%xWidth)[2:]), _padHex(hex(int(chunknum/xWidth)+1)[2:])]
        
        if cords[0] == '00':
            cords[0] = _padHex(hex(xWidth)[2:])
            cords[1] = _padHex(hex(int(chunknum/xWidth))[2:])
        
        if symbol == '00':
            bgColor = data[i+2:i+4]
            curKey = _tabKey(symbol, bgColor)
            prevKey = curKey
            
            if pix.get(curKey) == None:
                pix[curKey] = [cords]
            else:
                pix[curKey].append(cords)
            i = i + 4
            
        elif symbol != 'FF':
            bgColor = data[i+2:i+4]
            fgColor = data[i+4:i+6]
            curKey = _tabKey(symbol, bgColor, fgColor)
            prevKey = curKey
            
            if pix.get(curKey) == None:
                pix[curKey] = [cords]
            else:
                pix[curKey].append(cords)
            i = i + 6
            
        else: #symbol == 'FF'
            pix[prevKey].append(cords)
            i = i + 2
            
    return pix

#Called after tabularized data to create a string representation of the table
def _createTable(data, res):
    tmpList = []
    result = ''
    for k in data.keys():
        tmp = [k]
        for v in data[k]:
            tmp.append([v[0] + v[1]])
        tmpList.append(tmp)
    
    def keySortHR(i):
        if(len(i[0]) == 6):
            return (int(str(i[0][2:4]), 16)*1000 + int(str(i[0][4:6]), 16))
        else:
            return (int(str(i[0][2:4]), 16)*1000)
        
    def keySortLR(i):
        return (int(str(i[0][:2]), 16)*1000 + int(str(i[0][2:4]), 16))

    if res == hres:
        tmpList = sorted(tmpList, key=keySortHR, reverse=True)
    if res == lres:
        tmpList = sorted(tmpList, key=keySortLR, reverse=True)
    
    for k in tmpList:
        result = result + k[0]
        for v in k:
            if len(v[0]) == 1:
                continue
            result = result + v[0]
        result = result + '?'
    
    return result

#Convert hex string into byte array
#0x3F used as delimeter in data, convert to 0xFF delimeter in output
#0xFF in original data converted to 0xFE
def _hex2bytes(data):
    i = 0
    b = []
    while(i < len(data)):
        if data[i] == '?':
            b.append(255)
            i = i + 1
        else:
            tmp = int(data[i:i+2], 16)
            b.append(tmp)
            i = i + 2
    
    return bytes(b)

#Upload data to pastebin as unlisted and 10 minute expiration date
#@return url: byte array of the address on pastebin
def _paste2pastebin(data, dev_key):
    pastebin_args = {'api_dev_key':dev_key, 'api_paste_private': 1,'api_option':'paste', 'api_paste_code':data, 'api_paste_expire_date':'10M'}
    response = urllib.request.urlopen('http://pastebin.com/api/api_post.php', urllib.parse.urlencode(pastebin_args).encode('utf-8'))
    url = response.read()
    
    return url

#After repainting, get the symbols and color information for each chunk
def _postInit(pix, x_size, y_size, res):
    ylen = 4
    xlen = 2
    if res != hres:
        ylen = 2
        xlen = 1
    
    result = ''
    for y in range(0,y_size,ylen):
        for x in range(0,x_size,xlen):
            chunk = []
            
            for j in range(ylen):
                for i in range(xlen):
                    _getPix(pix, x+i, y+j, chunk)
     
            result = result + _getMixedData(chunk)

    return result

#Merge pixels and update the palette with available colors
def _initData(pix, x_size, y_size, res):
    ref = 4
    ylen = 4
    xlen = 2
    if res == lres:
        ylen = 2
        xlen = 1
        ref = 0
    
    for y in range(0,y_size,ylen):
        for x in range(0,x_size,xlen):
            chunk = []
            
            for j in range(ylen):
                for i in range(xlen):
                    _getPix(pix, x+i, y+j, chunk)
            
            _updateChunkAndPalette(chunk, ref)

            for j in range(ylen):
                for i in range(xlen):
                    idx = xlen*j+i
                    pix[x+i,y+j] = (chunk[idx][0], chunk[idx][1], chunk[idx][2])
    
    #merge similar colors across canvas
    pix = _repaintPix(pix, x_size, y_size)
    
    return _postInit(pix, x_size, y_size, res)

#Does heavy lifting for converting raw data to table data to byte array.
#Uploads to pastebin if dev key is provided
def _write2file(file, data, res, x_size, y_size, dev_key=None):
    xWidth = 160
    if res != hres and res != lres:
        print('Error - wrong resolution trying to write file', file=sys.stderr)
        return 
    
    data = _tabularizeData(data, res, xWidth)
    data = _createTable(data, res)
    data = _hex2bytes(data)
    
    header = sig
    header.append(vers)
    header.append(res)
    
    if res == 32:
        header.append(int(x_size/2))
        header.append(int(y_size/4))
    else:
        header.append(x_size)
        header.append(int(y_size/2))
    
    header.append(len(customPalette))
    for color in customPalette:
        for chan in color:
            header.append(chan)
    
    data = bytes(header) + data
                
    f = open(file[:-4] + '.bytes', 'wb')
    f.write(data)
    f.close()
    
    if(dev_key != None):
        url = _paste2pastebin(data, dev_key)
        print('Pastebin URL: ', url)
    
    return data

def quantizedColor(color):
    eMin = 10000
    result = color
    for quant_color in quantizedColors:
        tmpColor = quant_color[0], quant_color[1], quant_color[2]
        e = _getColorDist(color, tmpColor)
        if e < eMin:
            eMin = e
            result = tmpColor
    return result

#Converts a 160x100 or less pixel image into data for image.lua
#@param dev_key: string of dev key from pastebin
#@param file: string of absolute file path to image
#@return url: byte array of address of uploead on pastebin
def lowRes(file, colors=32, dev_key=None):
    im = Image.open(file)

    im = im.convert(mode='P', palette=Image.ADAPTIVE, colors=colors)

    im = im.convert('RGB')

    pix = im.load()
    
    x_size = im.size[0]
    y_size = im.size[1]
    
    if x_size > 160 or y_size > 100:
        print('Error - Image dimensions exceed range(160,100)(x,y): (%d, %d)\n' % (x_size, y_size), file=sys.stderr)
        return

    result = _initData(pix, x_size, y_size, lres)

    im.save(file[:file.rfind('/')] + '/preview.png')
    
    return _write2file(file, result, lres, x_size, y_size, dev_key)

#Converts a 320x200 or less pixel image into data for image.lua
#@param dev_key: string of dev key from pastebin
#@param file: string of absolute file path to image
#@return url: byte array of address of uploead on pastebin
def highRes(file, dither=False, colors=32, dev_key=None):
    pix = None
    im = Image.open(file)
    x_size = im.size[0]
    y_size = im.size[1]
    result = ''
    
    if x_size > 320 or y_size > 200:
        print('Error - Image dimensions exceed range(320,200)(x,y): (%d, %d)\n' % (x_size, y_size), file=sys.stderr)
        return
    
    if dither:
        dither = Dither.Dither(file).error_diffusion()
        im = dither.image
        pix = im.load()
        global customPalette 
        customPalette = dither.custom_palette
        result = _postInit(pix, x_size, y_size, hres)
    else:
        im = im.convert(mode='P', palette=Image.ADAPTIVE, colors=colors)
        im = im.convert('RGB')
    
        pix = im.load()
        
        result = _initData(pix, x_size, y_size, hres)

    im.save(file[:file.rfind('\\')] + '\\preview.png')
    
    return _write2file(file, result, hres, x_size, y_size, dev_key)

if __name__ == '__main__':
    filepath = ''
    res = ''
    devKey = None
    
    if len(sys.argv) > 3:
        filepath = sys.argv[1]
        res = sys.argv[2]
        dither = sys.argv[3]
    if len(sys.argv) > 4:    
        devKey = sys.argv[4]
    
    if res == 'hres':
        highRes(filepath, dither=dither, dev_key=devKey)
    elif res == 'lres':
        lowRes(filepath, dev_key=devKey)
    else:
        print('Usage: python <converter.py> <filepath_to_image> <resolution> <dev_key>')
        print('<filepath_to_image>: absolute path to image')
        print('<resolution>: hres or lres')
        print('<dither>: true or false')
        print('<dev_key>: optional pastebin developer key')