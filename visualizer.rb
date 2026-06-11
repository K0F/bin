################################
### VIZUALIZER BETA KOF 2012 ###
################################

#full_screen


def setup
  size 320,640,P2D

  header = "\n##################################\n# THIS IS VIZUALIZER BETA BY KOF #\n##################################\n\n"
  puts header

  textFont(createFont("Semplice Regular",8,false))
  textMode SCREEN


  background 0
  frameRate 50
  noCursor

  smooth

  @move = -2

  @filename = ARGF.filename


  loadit = Thread.new do


    @raw = loadBytes @filename

    @siz = (@raw.length)


    @graf = createGraphics(width,(@siz/width).to_i,P2D)
    @graf.beginDraw
    @graf.background 0
    @graf.endDraw

    puts "it has: "+@raw.size.to_s+" kb\nrendering ...\n\n"
    

    c = 0


    @graf.beginDraw

    (0..@graf.height).each do |y|
      (0..@graf.width).each do |x|

        @ready = y > height ? true : false

        @graf.set x,y,(color(@raw[c % @raw.size]))
        c += 1
      end
    end

    @done = true

    @graf.endDraw

  end

  @shift = 0

  puts "using file: "+@filename
  
end



def draw

  background 0

  if(@graf != NIL)
    image @graf,0,@shift
  end

  @shift += @ready ? @move : 0


  anim = [".","..","...","....",".....",".......","......."]

  textAlign RIGHT
  fill 255,0,0
  text(" #{anim[@shift%anim.size]}"+(@siz).to_s+" kb <==  "+@filename.split("/").at(-1),width-20,20);



end

def keyPressed

  if(keyCode == DOWN)
    @move -= 1
  elsif(keyCode == UP)
    @move += 1
  elsif(key==' ')
    @move = 0
  end

end

