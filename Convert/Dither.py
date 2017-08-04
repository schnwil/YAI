#Dithering class that uses Floyd-Steinberg. Creates a resulting image
#with each 2x4 pixel chunk contains at most 2 colors while also performing
#error distribution. 
#
#@author schnwil

from argparse import ArgumentParser
from PIL import Image
from _bisect import bisect_left

rv = [0, 51, 102, 153, 204, 255]
gv = [0, 36, 73, 109, 146, 182, 216, 255]
bv = [0, 64, 128, 192, 255]

coeff = [0,    0,    0,
         0,    0,    7/16, 
         6/16, 3/16, 1/16]

custom_palette = []

class Dither():
    def __init__(self, path, output=False):
        self.path = path
        self.pixel = None
        self.custom_palette = None
        self.output = output
        self.image = None
    
    def takeClosest(self, myList, myNumber):
        pos = bisect_left(myList, myNumber)
        if pos == 0:
            return myList[0], myList[1]
        if pos == len(myList):
            return myList[-1], myList[-2]
        before = myList[pos - 1]
        after = myList[pos]
        if after - myNumber < myNumber - before:
            return after, before
        else:
            return before, after
    
    def get_color_distance(self, color1, color2):
        return (color1[0] - color2[0])*(color1[0] - color2[0]) + (color1[1] - color2[1])*(color1[1] - color2[1]) + (color1[2] - color2[2])*(color1[2] - color2[2])
    
    def get_closest_palette_color(self, color_in):
        
        t = 1000000000 #max error
        best_match = [0,0,0,0]
        eMin = [t,t,t,t]
        for color in custom_palette:
            e = self.get_color_distance(color, color_in)
            for i in range(4):
                if e < eMin[i]:
                    eMin[i] = e
                    best_match[i] = color
                    break
                
        result = []
        for color in best_match:
            if color != 0:
                result.append(color)
        
        return result

    def get_quantized_color(self, color_in):
        red_oldpixel, green_oldpixel, blue_oldpixel = color_in

        red_newpixel = self.takeClosest(rv, red_oldpixel)[0]
        green_newpixel = self.takeClosest(gv, green_oldpixel)[0]
        blue_newpixel = self.takeClosest(bv, blue_oldpixel)[0]
        
        return red_newpixel, green_newpixel, blue_newpixel
    
    def distribute_error(self, pixel, x, y, x_lim, y_lim, color_org, color_use, doBackError=True):
        pixel[x,y] = color_use
        
        x = x - 1
        y = y - 1
        
        red_error = color_org[0] - color_use[0]
        green_error = color_org[1] - color_use[1]
        blue_error =  color_org[2] - color_use[2]
        
        for j in range(3):
            for i in range(3):
                local_coeff = coeff[j*3+i]
                
                if local_coeff == 0: continue
                if not doBackError and i == 0 and x % 2 == 1: continue
                
                xi = x + i
                yj = y + j
                
                if xi < x_lim and xi >= 0 and yj >= 0 and yj < y_lim:
                    
                    rc, gc, bc = pixel[xi, yj]
                    
                    red = rc + int(red_error * local_coeff)
                    green = gc + int(green_error * local_coeff)
                    blue = bc + int(blue_error * local_coeff)
                    
                    pixel[xi, yj] = (red, green, blue)

        return 
    
    def get_colors(self, pixel, x, y, x_step, y_step):
        colors = []
        for i in range(x_step):
            for j in range(y_step):
                tmp_color = pixel[x+i, y+j]
                
                color_found = False
                for c in colors:
                    if c[0] == tmp_color:
                        c[1] = c[1] + 1
                        color_found = True
                if not color_found:
                    colors.append([tmp_color, 1])
        
        def sort_key(i):
            return i[1]            
        
        colors = sorted(colors, key=sort_key, reverse=True)
          
        return colors
    
    def get_custom_palette(self, image_file, x_lim, y_lim):
        img = Image.open(image_file)
        img = img.convert('P', palette=Image.ADAPTIVE, colors=32)
        img = img.convert('RGB')
        pixel = img.load()
        
        colors = []
        for x in range(x_lim):
            for y in range(y_lim):
                color = pixel[x, y]
                colorFound = False
                for c in colors:
                    if c[0] == color:
                        c[1] += 1
                        colorFound = True
                if not colorFound:
                    colors.append([color, 1])
        
        def sortKey(self):
            return self[1]
        
        sorted_colors = sorted(colors, key=sortKey, reverse=True)
        
        for c in sorted_colors:
            if c[0] == (255,255,255):
                sorted_colors.pop(sorted_colors.index(c))
            if c[0] == (0,0,0):
                sorted_colors.pop(sorted_colors.index(c))
        
        for i in range(16):
            color = sorted_colors[i][0]
            custom_palette.append(color)

        return
    
    def get_chunk_colors(self, pixel, x, y):
        colors = []
        
        for yi in range(4):
            for xi in range(2):
                color_cur = pixel[x+xi, y+yi]
                color_q = self.get_quantized_color(color_cur)
                color_c = self.get_closest_palette_color(color_cur)
                
                if color_q not in colors:
                    colors.append(color_q)
                for i in range(4):
                    if color_c[i] not in colors:
                        colors.append(color_c[i])
        
        return colors
    
    def get_closest_color(self, color_in):
        c1 = self.get_closest_palette_color(color_in)
        c2 = self.get_quantized_color(color_in)
        c_org = color_in
        
        e1 = self.get_color_distance(c1, c_org)
        e2 = self.get_color_distance(c2, c_org)
        c_ret = c1
        if e2 < e1:
            c_ret = c2
        
        return c_ret
    
    def get_closest_palette(self, color_in):
        r_in = color_in[0]
        g_in = color_in[1]
        b_in = color_in[2]
        
        r_closest = self.takeClosest(rv, r_in)
        g_closest = self.takeClosest(gv, g_in)
        b_closest = self.takeClosest(bv, b_in)
        
        palette = []
        for r in r_closest:
            for g in g_closest:
                for b in b_closest:
                    palette.append((r,g,b))
                    
        palette += self.get_closest_palette_color(color_in)
        
        return palette
    
    def dither_chunk(self, img, pixel, x, y, x_step, y_step, x_lim, y_lim):
        crop_r = (x-1,y,x+x_step+1,y+y_step+1)
        palette = self.get_chunk_colors(pixel, x, y)

        color1 = 0
        color2 = 0
        eMin = 1000000000
        thresh_map = [0,0,0,0,0,0,0,0]
        x_lim_chunk, y_lim_chunk = x_step+2, y_step+1
        
        pal_len = len(palette)
        
        for i in range(pal_len):
            for j in range(i, pal_len):
                c1 = palette[i]
                c2 = palette[j]
                
                if c1 == c2: continue        
                
                crop_img = img.crop(crop_r)
                chunk_new = crop_img.load()
                local_map = [0,0,0,0,0,0,0,0]
                error = 0
                
                for yi in range(4):
                    if error > eMin: break
                    for xi in range(1,3):
                
                        color_org = chunk_new[xi,yi]
                        
                        e1 = self.get_color_distance(color_org, c1)
                        e2 = self.get_color_distance(color_org, c2)
                        
                        color_use = c1
                        if e2 < e1:
                            error += e2
                            color_use = c2
                            local_map[(xi-1)+yi*2] = 1
                        else:
                            error += e1
                            
                        if error > eMin: break
                        
                        self.distribute_error(chunk_new, xi, yi, x_lim_chunk, y_lim_chunk, color_org, color_use)
                        
                if error < eMin:
                    eMin = error
                    color1 = c1
                    color2 = c2
                    thresh_map = local_map
        
        for yi in range(4):
            for xi in range(2):
                color_org = pixel[x+xi, y+yi]
                
                if thresh_map[xi+yi*2] == 1:
                    self.distribute_error(pixel, x+xi, y+yi, x_lim, y_lim, color_org, color2, False)
                else:
                    self.distribute_error(pixel, x+xi, y+yi, x_lim, y_lim, color_org, color1, False)
           
        return color1, color2

    def error_diffusion(self):
        image_file = self.path
        new_img = Image.open(image_file)

        new_img = new_img.convert('RGB')
        pixel = new_img.load()

        x_lim, y_lim = new_img.size
        
        self.get_custom_palette(image_file, x_lim, y_lim)
        
        x_step = 2
        y_step = 4

        for y in range(0, y_lim, y_step):
            for x in range(0, x_lim, x_step):
                self.dither_chunk(new_img, pixel, x, y, x_step, y_step, x_lim, y_lim)
        
        self.pixel = pixel
        self.custom_palette = custom_palette
        self.image = new_img
        if self.output:
            idx = self.path.rfind('\\')
            output = self.path[:idx] + '\\preview.png'
            new_img.save(output)
            
        return self
