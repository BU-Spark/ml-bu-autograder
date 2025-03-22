/**
 * Selectable List Component for BU MET Autograder
 * UI component for selecting multiple submissions
 */

import React, { useEffect, useState, useRef } from 'react';
import {
  Box,
  Checkbox,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  Paper,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import PropTypes from 'prop-types';

// Styled components
const StyledListItem = styled(ListItem)(({ theme, selected, highlighted }) => ({
  marginBottom: theme.spacing(1),
  padding: 0,
  borderRadius: theme.shape.borderRadius,
  backgroundColor: highlighted
    ? `${theme.palette.primary.main}15`
    : selected
    ? `${theme.palette.action.selected}`
    : theme.palette.background.paper,
  border: `1px solid ${
    highlighted
      ? theme.palette.primary.main
      : selected
      ? theme.palette.action.selected
      : theme.palette.divider
  }`,
}));

const StyledListItemButton = styled(ListItemButton)(({ theme }) => ({
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(1.5, 2),
}));

// Multi-Selection List component
const SelectableList = ({
  items,
  keyField = 'id',
  secondaryKeyField = null,
  selectedItems = [],
  onSelectionChange,
  onItemClick,
  highlightedItem = null,
  selectionMode = 'none',
  renderItem,
}) => {
  const [selected, setSelected] = useState(selectedItems);
  const lastSelectedIndex = useRef(-1);

  // Update selected state when selectedItems prop changes
  useEffect(() => {
    setSelected(selectedItems);
  }, [selectedItems]);

  // Get unique key for an item
  const getItemKey = (item) => {
    if (secondaryKeyField) {
      return `${item[keyField]}-${item[secondaryKeyField]}`;
    }
    return item[keyField];
  };

  // Check if an item is selected
  const isSelected = (item) => {
    if (selectionMode === 'none') return false;

    const itemKey = getItemKey(item);
    return selected.includes(itemKey);
  };

  // Check if an item is highlighted
  const isHighlighted = (item) => {
    if (!highlightedItem) return false;

    return getItemKey(item) === getItemKey(highlightedItem);
  };

  // Handle item selection
  const handleSelection = (event, item, index) => {
    event.stopPropagation();

    if (selectionMode === 'none') return;

    const itemKey = getItemKey(item);
    let newSelected = [...selected];

    if (event.shiftKey && selectionMode === 'multiple' && lastSelectedIndex.current >= 0) {
      // Handle shift+click for range selection
      const start = Math.min(lastSelectedIndex.current, index);
      const end = Math.max(lastSelectedIndex.current, index);

      const keysToAdd = items
        .slice(start, end + 1)
        .map((i) => getItemKey(i))
        .filter((key) => !newSelected.includes(key));

      newSelected = [...newSelected, ...keysToAdd];
    } else {
      // Handle single item selection/deselection
      if (newSelected.includes(itemKey)) {
        newSelected = newSelected.filter((key) => key !== itemKey);
      } else {
        if (selectionMode === 'single') {
          newSelected = [itemKey];
        } else {
          newSelected.push(itemKey);
        }
      }
    }

    lastSelectedIndex.current = index;
    setSelected(newSelected);

    if (onSelectionChange) {
      onSelectionChange(newSelected);
    }
  };

  // Handle item click (not for selection)
  const handleItemClick = (item) => {
    if (onItemClick) {
      onItemClick(item);
    }
  };

  return (
    <Paper variant="outlined" sx={{ maxHeight: 600, overflow: 'auto' }}>
      {items.length === 0 ? (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No items available
          </Typography>
        </Box>
      ) : (
        <List disablePadding sx={{ p: 1 }}>
          {items.map((item, index) => {
            const isItemSelected = isSelected(item);
            const isItemHighlighted = isHighlighted(item);

            return (
              <StyledListItem
                key={getItemKey(item)}
                selected={isItemSelected}
                highlighted={isItemHighlighted}
                disablePadding
              >
                <StyledListItemButton
                  onClick={() => handleItemClick(item)}
                  selected={isItemSelected}
                >
                  {selectionMode !== 'none' && (
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <Checkbox
                        edge="start"
                        checked={isItemSelected}
                        tabIndex={-1}
                        disableRipple
                        onClick={(event) => handleSelection(event, item, index)}
                      />
                    </ListItemIcon>
                  )}

                  <Box sx={{ width: '100%' }}>
                    {renderItem ? renderItem(item) : getItemKey(item)}
                  </Box>
                </StyledListItemButton>
              </StyledListItem>
            );
          })}
        </List>
      )}
    </Paper>
  );
};

// PropTypes for type checking
SelectableList.propTypes = {
  items: PropTypes.array.isRequired,
  keyField: PropTypes.string,
  secondaryKeyField: PropTypes.string,
  selectedItems: PropTypes.array,
  onSelectionChange: PropTypes.func,
  onItemClick: PropTypes.func,
  highlightedItem: PropTypes.object,
  selectionMode: PropTypes.oneOf(['none', 'single', 'multiple']),
  renderItem: PropTypes.func,
};

export default SelectableList;