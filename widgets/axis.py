# axis.py
# package to handle an axis, and the conversion of data -> coordinates

#    Copyright (C) 2003 Jeremy S. Sanders
#    Email: Jeremy Sanders <jeremy@jeremysanders.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
##############################################################################

# $Id$

import numarray

import widget
import axisticks
import widgetfactory
import graph
import setting
import utils

class Axis(widget.Widget):
    """Manages and draws an axis."""

    typename = 'axis'
    allowedparenttypes = [graph.Graph]

    def __init__(self, parent, name=None):
        """Initialise axis."""

        widget.Widget.__init__(self, parent, name=name)
        s = self.settings
        s.add( setting.Str('label', '',
                           descr='Axis label text') )
        s.add( setting.FloatOrAuto('min', 'Auto',
                                   descr='Minimum value of axis') )
        s.add( setting.FloatOrAuto('max', 'Auto',
                                   descr='Maximum value of axis') )
        s.add( setting.Bool('log', False,
                            descr = 'Whether axis is logarithmic') )
        s.add( setting.Bool('autoExtend', True,
                            descr = 'Extend axis to nearest major tick') )
        s.add( setting.Bool('autoExtendZero', True,
                            descr = 'Extend axis to zero if close') )
        s.add( setting.Bool('autoMirror', True,
                            descr = 'Place axis on opposite side of graph '
                            'if none') )
        s.add( setting.Bool('reflect', False,
                            descr = 'Place axis text and ticks on other side'
                            ' of axis') )
        s.add( setting.Choice('direction',
                              ['horizontal', 'vertical'],
                              'horizontal',
                              descr = 'Direction of axis') )
        s.add( setting.Float('lowerPosition', 0.,
                             descr='Fractional position of lower end of '
                             'axis on graph') )
        s.add( setting.Float('upperPosition', 1.,
                             descr='Fractional position of upper end of '
                             'axis on graph') )
        s.add( setting.Float('otherPosition', 0.,
                             descr='Fractional position of axis '
                             'in its perpendicular direction') )

        s.add( setting.Line('Line',
                            descr = 'Axis line settings') )
        s.add( setting.MajorTick('MajorTicks',
                                 descr = 'Major tick line settings') )
        s.add( setting.MinorTick('MinorTicks',
                                 descr = 'Minor tick line settings') )
        s.add( setting.TickLabel('TickLabels',
                                 descr = 'Tick label settings') )
        s.add( setting.GridLine('GridLines',
                                descr = 'Grid line settings') )
        s.add( setting.AxisLabel('Label',
                                 descr = 'Axis label settings') )
        
        s.readDefaults()

        self.minorticks = None
        self.majorticks = None

        # we recompute the axis later
        s.setModified()

    def _autoLookupRange(self):
        """Automatically look up the plotable range
        from widgets that use this axis."""
        ourname = self.name

        # iterate over siblings to get axis range
        autorange = [1e99, -1e99]
        changed = False

        for c in self.parent.children:
            therange = c.autoAxis( ourname )
            # if range is wider, expand
            if therange != None:
                autorange[0] = min( therange[0], autorange[0] )
                autorange[1] = max( therange[1], autorange[1] )
                changed = True

        # return a default range if nobody gives us one
        if changed:
            return autorange
        else:
            if self.settings.log:
                return [1e-2, 1.]
            else:
                return [0., 1.]
                
    def _computePlottedRange(self):
        """Convert the range requested into a plotted range."""

        s = self.settings
        self.plottedrange = [s.min, s.max]

        # automatic lookup of minimum
        if s.min == 'Auto' or s.max == 'Auto':
            autorange = self._autoLookupRange()

            if s.min == 'Auto':
                self.plottedrange[0] = autorange[0]

            if s.max == 'Auto':
                self.plottedrange[1] = autorange[1]

        # work out tick values and expand axes if necessary
        
        as = axisticks.AxisTicks( self.plottedrange[0], self.plottedrange[1],
                                  s.MajorTicks.number, s.MinorTicks.number,
                                  extendbounds = s.autoExtend,
                                  extendzero = s.autoExtendZero,
                                  logaxis = s.log )

        (self.plottedrange[0],self.plottedrange[1],
         self.majortickscalc, self.minortickscalc) =  as.getTicks()

        if self.majorticks != None:
            self.majortickscalc = numarray.array(self.majorticks)

        if self.minorticks != None:
            self.minortickscalc = numarray.array(self.minorticks)

        self.settings.setModified(False)

    def _updatePlotRange(self, bounds):
        """Calculate coordinates on plotter of axis."""

        s = self.settings
        x1, y1, x2, y2 = bounds
        dx = x2 - x1
        dy = y2 - y1
        p1, p2, pp = s.lowerPosition, s.upperPosition, s.otherPosition

        if s.direction == 'horizontal': # horizontal
            self.coordParr1 = x1 + int(dx * p1)
            self.coordParr2 = x1 + int(dx * p2)

            # other axis coordinates
            self.coordPerp  = y2 - int(dy * pp)
            self.coordPerp1 = y2 - int(dy * p1)
            self.coordPerp2 = y2 - int(dy * p2)

        else: # vertical
            self.coordParr1 = y2 - int(dy * p1)
            self.coordParr2 = y2 - int(dy * p2)

            # other axis coordinates
            self.coordPerp  = x1 + int(dx * pp)
            self.coordPerp1 = x1 + int(dx * p1)
            self.coordPerp2 = x1 + int(dx * p2)
     
    def graphToPlotterCoords(self, bounds, vals):
        """Convert graph coordinates to plotter coordinates on this axis.

        bounds specifies the plot bounds
        vals is numarray of coordinates
        Returns positions as numarray of integers
        """

        # if the axis was modified, recompute the range
        if self.settings.isModified():
            self._computePlottedRange()

        self._updatePlotRange(bounds)

        return self._graphToPlotter(vals)

    def _graphToPlotter(self, vals):
        """Convert the coordinates assuming the machinery is in place."""
        
        # work out fractional posistions, then convert to pixels
        if self.settings.log:
            fracposns = self.logConvertToPlotter( vals )
        else:
            fracposns = self.linearConvertToPlotter( vals )

        # rounds to nearest integer
        out = numarray.floor( 0.5 +
                              self.coordParr1 +
                              fracposns*(self.coordParr2-self.coordParr1) )
        out = out.astype(numarray.Int32)
        return out
    
    def plotterToGraphCoords(self, bounds, vals):
        """Convert plotter coordinates on this axis to graph coordinates.
        
        bounds specifies the plot bounds
        vals is a numarray of coordinates
        returns a numarray of floats
        """
        # if the axis was modified, recompute the range

        if self.settings.isModified():
            self._computePlottedRange()

        self._updatePlotRange( bounds )

        # work out fractional positions of the plotter coords
        frac = ( ( vals.astype(numarray.Float64) - self.coordParr1 ) /
                 ( self.coordParr2 - self.coordParr1 ) )

        # scaling...
        if self.settings.log:
            return self.logConvertFromPlotter( frac )
        else:
            return self.linearConvertFromPlotter( frac )
        
    def linearConvertToPlotter(self, v):
        """Convert graph coordinates to fractional plotter units for linear scale.
        """
        return ( ( v - self.plottedrange[0] ) /
                 ( self.plottedrange[1]-self.plottedrange[0] ) )
    
    def linearConvertFromPlotter(self, v):
        """Convert from (fractional) plotter coords to graph coords.
        """
        return ( self.plottedrange[0] + v *
                 (self.plottedrange[1]-self.plottedrange[0] ) )
    
    def logConvertToPlotter(self, v):
        """Convert graph coordinates to fractional plotter units for log10 scale.
        """

        log1 = numarray.log(self.plottedrange[0])
        log2 = numarray.log(self.plottedrange[1])
        return ( numarray.log(v) - log1 )/( log2 - log1 )
    
    def logConvertFromPlotter(self, v):
        """Convert from fraction plotter coords to graph coords with log scale.
        """
        return ( self.plottedrange[0] *
                 ( self.plottedrange[1]/self.plottedrange[0] )**v )
    
    def swapline(self, painter, a1, b1, a2, b2):
        """ Draw line, but swap x & y coordinates if vertical axis."""
        if self.settings.direction == 'horizontal':
            painter.drawLine(a1, b1, a2, b2)
        else:
            painter.drawLine(b1, a1, b2, a2)

    _ticklabel_aligntable = {
        (0, 0, 0, 0): ( 0, 1), # horz, normal, nonrefl
        (0, 1, 0, 0): ( 1, 0), # horz, rot,    nonrefl
        (0, 0, 1, 0): ( 0,-1), # horz, normal, refl
        (0, 1, 1, 0): (-1, 0), # horz, rot,    refl
        (0, 0, 0,-1): (-1, 1), # horz, normal, nonrefl, first
        (0, 1, 0,-1): ( 1, 1), # horz, rot,    nonrefl, first
        (0, 0, 1,-1): ( 0,-1), # horz, normal, refl,    first FIXME
        (0, 1, 1,-1): (-1, 0), # horz, rot,    refl,    first FIXME
        (0, 0, 0, 1): ( 1, 1), # horz, normal, nonrefl, last
        (0, 1, 0, 1): ( 1,-1), # horz, rot,    nonrefl, last
        (0, 0, 1, 1): ( 0,-1), # horz, normal, refl,    last FIXME
        (0, 1, 1, 1): (-1, 0), # horz, rot,    refl,    last FIXME

        (1, 0, 0, 0): ( 1, 0), # vert, normal, nonrefl
        (1, 1, 0, 0): ( 0,-1), # vert, normal, nonrefl
        (1, 0, 1, 0): (-1, 0), # vert, normal, refl
        (1, 1, 1, 0): ( 0, 1), # vert, normal, refl
        (1, 0, 0,-1): ( 1,-1), # vert, normal, nonrefl, first
        (1, 1, 0,-1): (-1,-1), # vert, rot,    nonrefl, first
        (1, 0, 1,-1): ( 0,-1), # vert, normal, refl,    first FIXME
        (1, 1, 1,-1): (-1, 0), # vert, rot,    refl,    first FIXME
        (1, 0, 0, 1): ( 1, 1), # vert, normal, nonrefl, last
        (1, 1, 0, 1): ( 1,-1), # vert, rot,    nonrefl, last
        (1, 0, 1, 1): ( 0,-1), # vert, normal, refl,    last  FIXME
        (1, 1, 1, 1): (-1, 0), # vert, rot,    refl,    last FIXME
       }

    _axislabel_alignments = (
        (         # horizontal axis
        (0, 1),    # normal
        (1, 0)     # rotated
        ),(       # vertical axis
        (0, -1),   # normal
        (1, 0)     # rotated
        ))

    def _drawGridLines(self, painter, coordticks):
        """Draw grid lines on the plot."""
        
        painter.setPen( self.settings.get('GridLines').makeQPen(painter) )
        for t in coordticks:
            self.swapline( painter,
                           t, self.coordPerp1,
                           t, self.coordPerp2 )

    def _drawAxisLine(self, painter):
        """Draw the line of the axis."""

        painter.setPen( self.settings.get('Line').makeQPen(painter) )
        self.swapline( painter,
                       self.coordParr1, self.coordPerp,
                       self.coordParr2, self.coordPerp )        

    def _drawMinorTicks(self, painter):
        """Draw minor ticks on plot."""

        s = self.settings
        mt = s.get('MinorTicks')
        painter.setPen( mt.makeQPen(painter) )
        delta = mt.getLength(painter)
        minorticks = self._graphToPlotter(self.minortickscalc)

        if s.direction == 'vertical':
            delta *= -1
        if s.reflect:
            delta *= -1
        for t in minorticks:
            self.swapline( painter,
                           t, self.coordPerp,
                           t, self.coordPerp - delta )

    def _drawMajorTicks(self, painter, tickcoords):
        """Draw major ticks on the plot."""

        s = self.settings
        painter.setPen( s.get('MajorTicks').makeQPen(painter) )
        startdelta = s.get('MajorTicks').getLength(painter)
        delta = startdelta

        if s.direction == 'vertical':
            delta *= -1
        if s.reflect:
            delta *= -1
        for t in tickcoords:
            self.swapline( painter,
                           t, self.coordPerp,
                           t, self.coordPerp - delta )

        # account for ticks if they are in the direction of the label
        if startdelta < 0:
            self._delta_axis += abs(delta)

    def _getTickLabelAlign(self, isfirst, islast):
        if isfirst:
            f = -1
        elif islast:
            f = 1
        else:
            f = 0

        s = self.settings
        return Axis._ticklabel_aligntable[s.direction == 'vertical',
                                          s.TickLabels.rotate,
                                          s.reflect,
                                          f]
        
    def _drawTickLabels(self, painter, coordticks, sign):
        """Draw tick labels on the plot."""

        s = self.settings
        painter.setPen( s.get('TickLabels').makeQPen() )
        font = s.get('TickLabels').makeQFont(painter)
        painter.setFont(font)
        tl_spacing = ( painter.fontMetrics().leading() +
                       painter.fontMetrics().descent() )
        tl_ascent  = painter.fontMetrics().ascent()

        # work out font alignment
        angle = 0
        if s.TickLabels.rotate:
            angle = 270

        # plot numbers
        format = s.TickLabels.format
        maxwidth = 0
        for i in xrange(len(coordticks)):
            x = coordticks[i]
            y = self.coordPerp + sign*(self._delta_axis+tl_spacing)
            num = utils.formatNumber(self.majortickscalc[i], format)

            if s.direction == 'vertical':
                x, y = y, x

            ax, ay = self._getTickLabelAlign(i==0, i==len(coordticks)-1)
            #print x, y, ax, ay, num
            rec = utils.render( painter, font,
                                x, y, num,
                                ax, ay, angle )
            maxwidth = max(maxwidth, rec[2] - rec[0])

        # keep track of where we are
        self._delta_axis += tl_spacing
        if ( (s.direction == 'horizontal' and angle == 0) or
             (s.direction == 'vertical' and angle != 0) ):
            self._delta_axis += tl_ascent
        else:
            self._delta_axis += maxwidth

    def _drawAxisLabel(self, painter, sign):
        """Draw an axis label on the plot."""

        s = self.settings
        painter.setPen( s.get('Label').makeQPen() )
        font = s.get('Label').makeQFont(painter)
        painter.setFont(font)
        al_spacing = ( painter.fontMetrics().leading() +
                       painter.fontMetrics().descent() )

        # work out font alignment
        ax, ay = ( Axis._axislabel_alignments[s.direction == 'vertical']
                   [s.Label.rotate] )

        # if reflected, we want the opposite alignment
        if s.reflect:
            ax, ay = ( -ax, -ay )

        # angle of text
        if ( (s.direction == 'horizontal' and not s.Label.rotate) or
             (s.direction == 'verical' and s.Label.rotate) ):
            angle = 0
        else:
            angle = 270

        x = ( self.coordParr1 + self.coordParr2 ) / 2
        y = self.coordPerp + sign*(self._delta_axis+al_spacing)
        if s.direction == 'vertical':
            x, y = y, x

        utils.render(painter, font, x, y,
                     s.label,
                     ax, ay, angle)

    def _autoMirrorDraw(self, posn, painter, coordticks):
        """Mirror axis to opposite side of graph if there isn't
        an axis there already."""

        s = self.settings
        countaxis = 0
        for c in self.parent.children:
            try:
                if s.direction == c.settings.direction:
                    countaxis += 1
            except AttributeError:
                # if it's not an axis we get here
                pass

        # another axis in the same direction, so we don't mirror it
        if countaxis != 1:
            return

        # swap axis to other side
        other = s.otherPosition
        if other < 0.5:
            next = 1.
        else:
            next = 0.
        s.otherPosition = next

        s.reflect = not s.reflect
        self._updatePlotRange(posn)
        if not s.Line.hide:
            self._drawAxisLine(painter)
        if not s.MinorTicks.hide:
            self._drawMinorTicks(painter)
        if not s.MajorTicks.hide:
            self._drawMajorTicks(painter, coordticks)
        s.reflect = not s.reflect

        # put axis back
        s.otherPosition = other

    def draw(self, parentposn, painter):
        """Plot the axis on the painter."""

        s = self.settings

        # do plotting of children (does that make sense?)
        posn = widget.Widget.draw(self, parentposn, painter)

        # recompute if modified
        if self.settings.isModified():
            self._computePlottedRange()

        self._updatePlotRange(posn)

        # get tick vals
        coordticks = self._graphToPlotter(self.majortickscalc)

        # save the state of the painter for later
        painter.save()

        # multiplication factor if reflection on the axis is requested
        sign = 1
        if s.direction == 'vertical':
            sign *= -1
        if s.reflect:
            sign *= -1

        # plot gridlines
        if not s.GridLines.hide:
            self._drawGridLines(painter, coordticks)

        # plot the line along the axis
        if not s.Line.hide:
            self._drawAxisLine(painter)

        # plot minor ticks
        if not s.MinorTicks.hide:
            self._drawMinorTicks(painter)

        # keep track of distance from axis
        self._delta_axis = 0

        # plot major ticks
        if not s.MajorTicks.hide:
            self._drawMajorTicks(painter, coordticks)

        # plot tick labels
        if not s.TickLabels.hide:
            self._drawTickLabels(painter, coordticks, sign)

        # draw an axis label
        if not s.Label.hide:
            self._drawAxisLabel(painter, sign)

        # mirror axis at other side of plot
        if s.autoMirror:
            self._autoMirrorDraw(posn, painter, coordticks)

        # restore the state of the painter
        painter.restore()

# allow the factory to instantiate an axis
widgetfactory.thefactory.register( Axis )
